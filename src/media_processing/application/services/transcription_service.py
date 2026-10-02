# src/media_processing/application/services/transcription_service.py
from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path
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
    TranscriptionTaskSchedulerPort,
    VisualDescriberPort,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.domain.processing_deadline import expected_processing_seconds
from src.shared.application.ports import ProcessingStatsPort
from src.shared.domain.errors import ResourceNotFoundError
from src.shared.domain.events import (
    MediaProcessingStarted,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.application.event_bus import SupportsEventBus

# DTOs
from ..dtos import (
    GetTranscriptionByIdQuery,
    GetTranscriptionByMediaIdQuery,
    RequestTranscriptionCommand,
    SetSpeakerAliasesCommand,
)

logger = structlog.get_logger(__name__)


class TranscriptionService:
    """Handle transcription operations: request, execute, and manage results."""

    def __init__(
        self,
        transcription_repo: TranscriptionRepositoryPort,
        task_scheduler: TranscriptionTaskSchedulerPort,
        transcription_logger: OperationLoggerPort,
        transcription_metrics: MetricsPort,
        storage_service: StoragePort,
        speech_recognizer_factory: SpeechRecognizerFactory,
        event_bus: SupportsEventBus | None = None,
        stats_recorder: ProcessingStatsPort | None = None,
        duration_probe: MediaDurationProbe | None = None,
        visual_describer: VisualDescriberPort | None = None,  # só no worker
    ) -> None:
        self._repo = transcription_repo
        self._task_scheduler = task_scheduler
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
        """Executes the transcription process: download, transcribe, and publish."""
        if self._event_bus:
            await self._event_bus.publish(
                MediaProcessingStarted(
                    media_id=str(media_id),
                    stage="transcription",
                    correlation_id=correlation_id,
                )
            )

        transcription = await self._repo.get_by_id(transcription_id)
        if not transcription:
            raise ResourceNotFoundError("Transcription", str(transcription_id))
        transcription.mark_as_processing()
        await self._repo.save(transcription)

        # Retrieve File
        content = await self._storage.retrieve(file_path)
        if not content:
            raise ResourceNotFoundError("File", file_path)

        # Write to temp
        suffix = Path(file_path).suffix or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        await self._record_media_duration(transcription, tmp_path)

        started = time.perf_counter()
        try:
            lang_for_model = None if not language or language.lower() == "auto" else language
            recognizer = self._speech_recognizer_factory(transcription_provider)
            # Support both sync and async recognizers
            if asyncio.iscoroutinefunction(recognizer.transcribe):
                result = await recognizer.transcribe(tmp_path, language=lang_for_model)
            else:
                result = await asyncio.to_thread(
                    recognizer.transcribe,
                    tmp_path,
                    language=lang_for_model,
                )

            await self._record_duration(
                time.perf_counter() - started, len(content), result, recognizer, "success"
            )

            # Em vídeos, descreve alguns quadros com o arquivo já em mãos.
            visual_context = await self._describe_frames(result, content, file_path, transcription)

            await self.process_transcription_result(
                transcription_id,
                media_id,
                result,
                transcription_provider,
                success=True,
                final_attempt=final_attempt,
                correlation_id=correlation_id,
                visual_context=visual_context,
            )
            return result
        except Exception as exc:
            await self._record_duration(
                time.perf_counter() - started, len(content), {}, transcription_provider, "failed"
            )
            await self.process_transcription_result(
                transcription_id,
                media_id,
                {},
                transcription_provider,
                success=False,
                error_message=str(exc),
                final_attempt=final_attempt,
                correlation_id=correlation_id,
            )
            raise
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def estimate_processing(self, media_id: UUID) -> Dict[str, Any]:
        """Estimativa do processamento completo de uma mídia.

        Usa a duração da gravação (lida pelo worker ao iniciar) e o tempo que
        as transcrições e análises anteriores levaram por segundo de gravação
        nesta instalação (processing_stats).
        """
        transcription = await self._repo.get_by_media_id(media_id)
        media_seconds = transcription.media_duration_seconds if transcription else None
        factors: Dict[str, Optional[float]] = {"transcription": None, "text_analysis": None}
        if media_seconds and self._stats:
            for task in factors:
                try:
                    factors[task] = await self._stats.realtime_factor(task)
                except Exception as exc:
                    logger.warning("transcription.estimate_factor_failed", task=task, error=str(exc))
        seconds = expected_processing_seconds(
            media_seconds, factors["transcription"], factors["text_analysis"]
        )
        return {
            "estimated_seconds": round(seconds) if seconds else None,
            "media_seconds": media_seconds,
            "includes_analysis": factors["text_analysis"] is not None,
        }

    async def _describe_frames(
        self, result: Dict[str, Any], content: bytes, file_path: str, transcription: Transcription
    ) -> List[str]:
        if not self._visual:
            return []
        segments = result.get("segments") or []
        last_end = segments[-1].get("end") if segments and isinstance(segments[-1], dict) else None
        return await self._visual.describe_recording(
            content, file_path, last_end or transcription.media_duration_seconds
        )

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
        segments = (result or {}).get("segments") or []
        media_seconds = segments[-1].get("end") if segments and isinstance(segments[-1], dict) else None
        model = recognizer if isinstance(recognizer, str) else (
            getattr(recognizer, "model_label", None) or type(recognizer).__name__
        )
        try:
            await self._stats.log_stat("transcription", seconds, size, media_seconds, model, status)
        except Exception as exc:  # estatística nunca pode derrubar a transcrição
            logger.warning("transcription.stats_record_failed", error=str(exc))

    async def request_transcription_generation(
        self, command: RequestTranscriptionCommand
    ) -> Dict[str, Any]:
        """Orchestrates the process of requesting a new transcription."""
        start_time = time.monotonic()
        success = False
        transcription_id: Optional[UUID] = None

        try:
            # 1. Create a PENDING transcription record
            transcription = Transcription(
                media_id=command.media_id,
                user_id=command.user_id,
                filename=command.filename,
                correlation_id=command.correlation_id,
                language=command.language,
                provider=command.transcription_provider,
                status=TranscriptionStatus.PENDING,
            )
            saved_transcription = await self._repo.save(transcription)
            transcription_id = saved_transcription.id

            # 2. Schedule the actual processing task
            task_info = await self._task_scheduler.schedule_transcription(
                transcription_id=transcription_id,
                media_id=command.media_id,
                file_path=command.file_path,
                storage_provider=command.storage_provider,
                transcription_provider=command.transcription_provider,
                language=command.language,
                file_size_bytes=command.file_size_bytes,
                user_id=str(command.user_id) if command.user_id else None,
                filename=command.filename,
                triggered_by=command.triggered_by,
                actor_id=command.actor_id,
                correlation_id=command.correlation_id,
            )
            success = True
            if hasattr(self._logger, "log_operation"):
                log_fn = self._logger.log_operation
                payload = dict(
                    operation="request_transcription_generation",
                    media_id=str(command.media_id),
                    transcription_id=str(transcription_id),
                    status="SCHEDULED",
                )
                if asyncio.iscoroutinefunction(log_fn):
                    await log_fn(**payload)
                else:
                    log_fn(**payload)
            return {
                "task_id": task_info.get("task_id"),
                "transcription_id": str(transcription_id),
            }
        finally:
            if hasattr(self._metrics, "set_context"):
                ctx = self._metrics.set_context
                if asyncio.iscoroutinefunction(ctx):
                    await ctx(str(command.media_id))
                else:
                    ctx(str(command.media_id))
            if hasattr(self._metrics, "record_operation"):
                rec = self._metrics.record_operation
                payload = dict(
                    operation="request_transcription",
                    provider=command.transcription_provider,
                    duration=time.monotonic() - start_time,
                    success=success,
                    status="SCHEDULED" if success else "FAILED",
                )
                if asyncio.iscoroutinefunction(rec):
                    await rec(**payload)
                else:
                    rec(**payload)

    async def set_speaker_aliases(
        self, command: SetSpeakerAliasesCommand
    ) -> Transcription:
        """Sets or updates speaker aliases for a given transcription."""
        transcription = await self._repo.get_by_id(command.transcription_id)
        if not transcription:
            raise ResourceNotFoundError("Transcription", str(command.transcription_id))
        transcription.set_speaker_aliases(command.aliases)
        return await self._repo.save(transcription)

    async def get_transcription_by_media_id(
        self, query: GetTranscriptionByMediaIdQuery
    ) -> Optional[Transcription]:
        """Retrieves transcription by media ID."""
        return await self._repo.get_by_media_id(query.media_id)

    async def get_transcription_by_id(
        self, query: GetTranscriptionByIdQuery
    ) -> Optional[Transcription]:
        """Retrieves transcription by its ID."""
        return await self._repo.get_by_id(query.transcription_id)

    # --- Callbacks from processing tasks ---
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
        """Handles the result of an asynchronous transcription task."""
        transcription = await self._repo.get_by_id(transcription_id)
        if not transcription:
            self._logger.error(
                "transcription.process_result.not_found",
                transcription_id=str(transcription_id),
            )
            return

        original_status = transcription.status
        if success:
            transcription.mark_as_completed(result_data)
            if visual_context:
                transcription.attach_visual_context(visual_context)
        else:
            if final_attempt:
                transcription.mark_as_failed(error_message or "Erro desconhecido")
            else:
                transcription.record_processing_error(
                    error_message or "Erro durante tentativa de processamento"
                )

        await self._repo.save(transcription)

        await self._record_result_observability(
            transcription, media_id, result_data, provider, success,
            error_message, original_status,
        )

        if not self._event_bus:
            return
        if success:
            await self._event_bus.publish(
                TranscriptionCompleted(
                    media_id=str(media_id),
                    transcription_id=str(transcription_id),
                    user_id=str(transcription.user_id) if transcription.user_id else None,
                    text=transcription.text,
                    provider=provider,
                    language=transcription.language,
                    confidence=transcription.confidence_score,
                    filename=transcription.filename,
                    correlation_id=correlation_id,
                )
            )
        elif final_attempt:
            await self._event_bus.publish(
                TranscriptionFailed(
                    media_id=str(media_id),
                    transcription_id=str(transcription_id),
                    user_id=str(transcription.user_id) if transcription.user_id else None,
                    error_message=error_message,
                    provider=provider,
                    correlation_id=correlation_id,
                )
            )

    async def _record_result_observability(
        self,
        transcription: Transcription,
        media_id: UUID,
        result_data: Dict[str, Any],
        provider: str,
        success: bool,
        error_message: Optional[str],
        original_status: TranscriptionStatus,
    ) -> None:
        """Registra o resultado no log e nas métricas."""
        if asyncio.iscoroutinefunction(getattr(self._logger, "log_operation", None)):
            await self._logger.log_operation(
                operation="process_transcription_result",
                media_id=str(media_id),
                provider=provider,
                success=success,
                duration=result_data.get("duration") or 0.0,
                transcription_id=str(transcription.id),
                status="COMPLETED" if success else "FAILED",
                original_status=original_status.value,
                error_message=error_message,
            )
        if hasattr(self._metrics, "set_context"):
            maybe = self._metrics.set_context
            if asyncio.iscoroutinefunction(maybe):
                await maybe(str(media_id))
            else:
                maybe(str(media_id))
        if hasattr(self._metrics, "record_operation"):
            record = self._metrics.record_operation
            duration = result_data.get("duration") or 0.0
            input_len = result_data.get("input_audio_length_seconds") or 0.0
            payload = dict(
                operation="process_transcription_result",
                provider=provider,
                success=success,
                status=transcription.status.value,
                duration=duration,
                input_audio_length_seconds=input_len,
                output_text_length_chars=len(transcription.text),
            )
            if asyncio.iscoroutinefunction(record):
                await record(**payload)
            else:
                record(**payload)
