"""Marca como falha as transcrições que passaram do prazo.

Executado periodicamente pelo worker leve (Celery beat). A falha segue o
mesmo caminho de uma falha comum: TranscriptionFailed marca a mídia como
falha e avisa o usuário, que pode então tentar novamente.
"""
from __future__ import annotations

import datetime
from typing import List, Optional

import structlog

from src.media_processing.application.ports import (
    ProcessingTaskTerminator,
    RealtimeFactorPort,
    TranscriptionResultPort,
    UnfinishedTranscriptionsPort,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.domain.processing_deadline import ProcessingDeadlinePolicy

logger = structlog.get_logger(__name__)


def _minutes(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes >= 120:
        return f"{minutes // 60} h"
    return f"{minutes} min"


class StalledProcessingMonitor:
    def __init__(
        self,
        repository: UnfinishedTranscriptionsPort,
        transcription_service: TranscriptionResultPort,
        policy: ProcessingDeadlinePolicy,
        realtime_factors: Optional[RealtimeFactorPort] = None,
        terminator: Optional[ProcessingTaskTerminator] = None,
    ) -> None:
        self._repo = repository
        self._transcriptions = transcription_service
        self._policy = policy
        self._realtime_factors = realtime_factors
        self._terminator = terminator

    async def sweep(self, now: Optional[datetime.datetime] = None) -> List[str]:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        # Nenhum prazo é menor que o mínimo: o banco devolve só as candidatas.
        candidates = await self._repo.list_unfinished(
            now - datetime.timedelta(seconds=self._policy.minimum_seconds)
        )
        if not candidates:
            return []

        factor = None
        if self._realtime_factors:
            try:
                factor = await self._realtime_factors.realtime_factor("transcription")
            except Exception as exc:  # sem histórico, vale o fator padrão
                logger.warning("stalled_monitor.realtime_factor_failed", error=str(exc))

        failed: List[str] = []
        for transcription in candidates:
            if not self._policy.is_stalled(transcription, now, factor):
                continue
            await self._fail(transcription, factor)
            failed.append(str(transcription.media_id))
        return failed

    async def _fail(self, transcription: Transcription, factor: Optional[float]) -> None:
        deadline = self._policy.deadline_for(transcription, factor) or 0
        if transcription.status == TranscriptionStatus.PENDING:
            message = (
                f"O processamento não começou em {_minutes(deadline)}; a tarefa pode ter "
                "se perdido na fila. Tente novamente."
            )
        else:
            message = (
                f"O processamento passou do tempo esperado ({_minutes(deadline)}) e foi "
                "interrompido. Tente novamente; se voltar a acontecer, o arquivo pode "
                "ser grande demais para esta máquina."
            )
            # Uma tarefa travada ocupa o worker pesado e segura toda a fila.
            if self._terminator:
                try:
                    await self._terminator.terminate(str(transcription.id), str(transcription.media_id))
                except Exception as exc:
                    logger.warning("stalled_monitor.terminate_failed", error=str(exc))

        logger.warning(
            "stalled_monitor.marking_failed",
            media_id=str(transcription.media_id),
            transcription_id=str(transcription.id),
            status=transcription.status.value,
            deadline_seconds=round(deadline),
            realtime_factor=factor,
        )
        await self._transcriptions.process_transcription_result(
            transcription.id,
            transcription.media_id,
            {},
            transcription.provider,
            success=False,
            error_message=message,
            final_attempt=True,
            correlation_id=transcription.correlation_id,
        )
