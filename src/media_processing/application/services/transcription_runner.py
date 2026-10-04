"""Execução da transcrição no worker: arquivo, modelo de fala, quadros e resultado.

Separada do agendamento e das consultas (TranscriptionService), que rodam na
API: o worker conhece o modelo de fala e o de visão; a API, só a fila.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.media_processing.application.ports import (
    MediaDurationProbe,
    MetricsPort,
    OperationLoggerPort,
    SpeechRecognizerFactory,
    StoragePort,
    TranscriptionRepositoryPort,
    VisualDescriberPort,
)
from src.media_processing.application.services.processing_job import (
    StagedFile,
    announce_started,
    staged_file,
)
from src.media_processing.domain import InvalidTranscriptionTransitionError, Transcription
from src.shared.application.event_bus import SupportsEventBus
from src.shared.application.ports import ProcessingStatsPort
from src.shared.domain.errors import ResourceNotFoundError
from src.shared.domain.events import TranscriptionCompleted, TranscriptionFailed

logger = structlog.get_logger(__name__)


def _last_segment_end(result: Dict[str, Any]) -> Optional[float]:
    segments = (result or {}).get("segments") or []
    return segments[-1].get("end") if segments and isinstance(segments[-1], dict) else None


class TranscriptionRunner:
    def __init__(
        self,
        transcription_repo: TranscriptionRepositoryPort,
        transcription_logger: OperationLoggerPort,
        transcription_metrics: MetricsPort,
        storage_service: StoragePort,
        speech_recognizer_factory: SpeechRecognizerFactory,
        event_bus: SupportsEventBus | None = None,
        stats_recorder: ProcessingStatsPort | None = None,
        duration_probe: MediaDurationProbe | None = None,
        visual_describer: VisualDescriberPort | None = None,
    ) -> None:
        self._repo = transcription_repo
        self._logger = transcription_logger
        self._metrics = transcription_metrics
        self._storage = storage_service
        self._speech_recognizer_factory = speech_recognizer_factory
        self._event_bus = event_bus
        self._stats = stats_recorder
        self._duration_probe = duration_probe
        self._visual = visual_describer

    async def execute_transcription(
        self,
        transcription_id: UUID,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        *,
        final_attempt: bool = False,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Baixa o arquivo para o disco, transcreve, descreve os quadros e publica."""
        transcription = await self._repo.get_by_id(transcription_id)
        if not transcription:
            raise ResourceNotFoundError("Transcription", str(transcription_id))
        if transcription.is_finished:
            # Tarefa entregue de novo (fila) ou repetida: não refaz o trabalho na GPU.
            logger.warning("transcription.already_finished", transcription_id=str(transcription_id))
            return {}
        await announce_started(self._event_bus, media_id, "transcription", correlation_id)
        transcription.mark_as_processing()
        await self._repo.save(transcription)

        started, size = time.perf_counter(), 0
        try:
            async with staged_file(self._storage, file_path) as media_file:
                size = media_file.size_bytes
                await self._record_media_duration(transcription, media_file.path)
                started = time.perf_counter()
                recognizer = self._speech_recognizer_factory(transcription_provider)
                lang_for_model = None if not language or language.lower() == "auto" else language
                result = await recognizer.transcribe(media_file.path, language=lang_for_model)
                await self._record_duration(time.perf_counter() - started, size, result, recognizer, "success")
                # Em vídeos, descreve alguns quadros com o arquivo ainda em disco.
                visual_context = await self._describe_frames(result, media_file, transcription)
        except Exception as exc:
            await self._record_duration(time.perf_counter() - started, size, {}, transcription_provider, "failed")
            await self.process_transcription_result(
                transcription_id, media_id, {}, transcription_provider, success=False,
                error_message=str(exc), final_attempt=final_attempt, correlation_id=correlation_id,
            )
            raise
        await self.process_transcription_result(
            transcription_id, media_id, result, transcription_provider, success=True,
            final_attempt=final_attempt, correlation_id=correlation_id, visual_context=visual_context,
        )
        return result

    async def process_transcription_result(
        self,
        transcription_id: UUID,
        media_id: UUID,
        result_data: Dict[str, Any],
        provider: str,
        success: bool,
        error_message: Optional[str] = None,
        *,
        final_attempt: bool = False,
        correlation_id: Optional[str] = None,
        visual_context: Optional[List[str]] = None,
    ) -> None:
        """Grava o resultado (ou a falha) e anuncia aos demais módulos."""
        transcription = await self._repo.get_by_id(transcription_id)
        if not transcription:
            logger.error("transcription.process_result.not_found", transcription_id=str(transcription_id))
            return

        original_status = transcription.status
        try:
            self._apply_result(transcription, result_data, success, error_message, final_attempt, visual_context)
        except InvalidTranscriptionTransitionError as exc:
            # Ex.: o prazo venceu e a transcrição já foi dada como falha.
            logger.warning("transcription.stale_result_ignored", transcription_id=str(transcription_id), reason=str(exc))
            return
        await self._repo.save(transcription)

        await self._record_result_observability(
            transcription, media_id, result_data, provider, success, error_message, original_status
        )
        await self._announce_result(
            transcription, media_id, provider, success, error_message, final_attempt, correlation_id
        )

    @staticmethod
    def _apply_result(transcription, result_data, success, error_message, final_attempt, visual_context) -> None:
        if success:
            transcription.mark_as_completed(result_data)
            if visual_context:
                transcription.attach_visual_context(visual_context)
        elif final_attempt:
            transcription.mark_as_failed(error_message or "Erro desconhecido")
        else:
            transcription.record_processing_error(error_message or "Erro durante tentativa de processamento")

    async def _announce_result(
        self, transcription, media_id, provider, success, error_message, final_attempt, correlation_id
    ) -> None:
        if not self._event_bus or not (success or final_attempt):
            return
        user_id = str(transcription.user_id) if transcription.user_id else None
        if success:
            event = TranscriptionCompleted(
                media_id=str(media_id), transcription_id=str(transcription.id), user_id=user_id,
                text=transcription.text, provider=provider, language=transcription.language,
                confidence=transcription.confidence_score, filename=transcription.filename,
                correlation_id=correlation_id,
            )
        else:
            event = TranscriptionFailed(
                media_id=str(media_id), transcription_id=str(transcription.id), user_id=user_id,
                error_message=error_message, provider=provider, correlation_id=correlation_id,
            )
        await self._event_bus.publish(event)

    async def _describe_frames(
        self, result: Dict[str, Any], media_file: StagedFile, transcription: Transcription
    ) -> List[str]:
        if not self._visual:
            return []
        duration = _last_segment_end(result) or transcription.media_duration_seconds
        return await self._visual.describe_recording(media_file.path, media_file.size_bytes, duration)

    async def _record_media_duration(self, transcription: Transcription, path: str) -> None:
        """Guarda a duração da gravação: define o prazo desta tentativa (ver
        ProcessingDeadlinePolicy) antes que a transcrição termine."""
        if not self._duration_probe:
            return
        try:
            seconds = await self._duration_probe.duration_seconds(path)
            if seconds:
                transcription.record_media_duration(seconds)
                await self._repo.save(transcription)
        except Exception as exc:  # a duração é auxiliar; nunca derruba a transcrição
            logger.warning("transcription.media_duration_failed", error=str(exc))

    async def _record_duration(
        self, seconds: float, size: int, result: Dict[str, Any], recognizer: Any, status: str
    ) -> None:
        """Grava quanto tempo a transcrição levou (para avaliação e estimativas)."""
        if not self._stats:
            return
        model = recognizer if isinstance(recognizer, str) else (
            getattr(recognizer, "model_label", None) or type(recognizer).__name__
        )
        try:
            await self._stats.log_stat("transcription", seconds, size, _last_segment_end(result), model, status)
        except Exception as exc:  # estatística nunca pode derrubar a transcrição
            logger.warning("transcription.stats_record_failed", error=str(exc))

    async def _record_result_observability(
        self, transcription, media_id, result_data, provider, success, error_message, original_status
    ) -> None:
        """Registra o resultado no log e nas métricas."""
        await self._logger.log_operation(
            operation="process_transcription_result",
            media_id=str(media_id),
            provider=provider,
            success=success,
            duration=result_data.get("duration") or 0.0,
            transcription_id=str(transcription.id),
            status="COMPLETED" if success else "FAILED",
            original_status=getattr(original_status, "value", original_status),
            error_message=error_message,
        )
        await self._metrics.record_operation(
            operation="process_transcription_result",
            provider=provider,
            success=success,
            status=transcription.status.value,
            duration=result_data.get("duration") or 0.0,
            input_audio_length_seconds=result_data.get("input_audio_length_seconds") or 0.0,
            output_text_length_chars=len(transcription.text or ""),
        )


__all__ = ["TranscriptionRunner"]
