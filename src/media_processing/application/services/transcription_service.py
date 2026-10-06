"""Transcrições vistas pela API: agendar, estimar e consultar.

A execução (modelo de fala, quadros do vídeo, resultado) fica no worker, em
TranscriptionRunner.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.application.ports import (
    MetricsPort,
    OperationLoggerPort,
    TranscriptionRepositoryPort,
    TranscriptionTaskSchedulerPort,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.domain.processing_deadline import expected_processing_seconds
from src.shared.application.ports import ProcessingStatsPort
from src.shared.application.access import Requester, ensure_can_access
from src.shared.domain.errors import NotFoundError

from ..dtos import (
    GetTranscriptionByIdQuery,
    GetTranscriptionByMediaIdQuery,
    RequestTranscriptionCommand,
    SetSpeakerAliasesCommand,
)

logger = structlog.get_logger(__name__)

NOT_FOUND = "Transcrição não encontrada"


class TranscriptionService:
    def __init__(
        self,
        transcription_repo: TranscriptionRepositoryPort,
        task_scheduler: TranscriptionTaskSchedulerPort,
        transcription_logger: OperationLoggerPort,
        transcription_metrics: MetricsPort,
        stats_recorder: ProcessingStatsPort | None = None,
    ) -> None:
        self._repo = transcription_repo
        self._task_scheduler = task_scheduler
        self._logger = transcription_logger
        self._metrics = transcription_metrics
        self._stats = stats_recorder

    async def request_transcription_generation(self, command: RequestTranscriptionCommand) -> Dict[str, Any]:
        """Cria o registro pendente e agenda a tarefa no worker."""
        start_time = time.monotonic()
        success = False
        try:
            transcription = await self._repo.save(
                Transcription(
                    media_id=command.media_id,
                    user_id=command.user_id,
                    filename=command.filename,
                    correlation_id=command.correlation_id,
                    language=command.language,
                    provider=command.transcription_provider,
                    status=TranscriptionStatus.PENDING,
                )
            )
            task_info = await self._task_scheduler.schedule_transcription(
                transcription_id=transcription.id,
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
            await self._logger.log_operation(
                operation="request_transcription_generation",
                media_id=str(command.media_id),
                transcription_id=str(transcription.id),
                status="SCHEDULED",
            )
            return {"task_id": task_info.get("task_id"), "transcription_id": str(transcription.id)}
        finally:
            await self._metrics.record_operation(
                operation="request_transcription",
                provider=command.transcription_provider,
                duration=time.monotonic() - start_time,
                success=success,
                status="SCHEDULED" if success else "FAILED",
            )

    async def estimate_processing(self, media_id: UUID, requester: Requester) -> Dict[str, Any]:
        """Estimativa do processamento completo de uma mídia.

        Usa a duração da gravação (lida pelo worker ao iniciar) e o tempo que
        as transcrições e análises anteriores levaram por segundo de gravação
        nesta instalação (processing_stats). Sem registro ainda (logo após o
        envio), não há estimativa.
        """
        transcription = await self._repo.get_by_media_id(media_id)
        if transcription is not None:
            ensure_can_access(transcription.user_id, requester, NOT_FOUND)
        media_seconds = transcription.media_duration_seconds if transcription else None
        factors: Dict[str, Optional[float]] = {"transcription": None, "text_analysis": None}
        if media_seconds and self._stats:
            for task in factors:
                try:
                    factors[task] = await self._stats.realtime_factor(task)
                except Exception as exc:
                    logger.warning("transcription.estimate_factor_failed", task=task, error=str(exc))
        seconds = expected_processing_seconds(media_seconds, factors["transcription"], factors["text_analysis"])
        return {
            "estimated_seconds": round(seconds) if seconds else None,
            "media_seconds": media_seconds,
            "includes_analysis": factors["text_analysis"] is not None,
        }

    async def set_speaker_aliases(self, command: SetSpeakerAliasesCommand, requester: Requester) -> Transcription:
        """Nomes dos falantes (para quando a transcrição os identificar)."""
        transcription = await self._accessible(await self._repo.get_by_id(command.transcription_id), requester)
        transcription.set_speaker_aliases(command.aliases)
        return await self._repo.save(transcription)

    async def get_transcription_by_media_id(
        self, query: GetTranscriptionByMediaIdQuery, requester: Requester
    ) -> Transcription:
        return await self._accessible(await self._repo.get_by_media_id(query.media_id), requester)

    async def get_transcription_by_id(self, query: GetTranscriptionByIdQuery, requester: Requester) -> Transcription:
        return await self._accessible(await self._repo.get_by_id(query.transcription_id), requester)

    @staticmethod
    async def _accessible(transcription: Optional[Transcription], requester: Requester) -> Transcription:
        """Inexistente ou de outro usuário: 404 (o dono é o da mídia, gravado na transcrição)."""
        if transcription is None:
            raise NotFoundError(NOT_FOUND)
        ensure_can_access(transcription.user_id, requester, NOT_FOUND)
        return transcription


__all__ = ["TranscriptionService"]
