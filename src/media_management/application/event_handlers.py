"""Reações do módulo de mídias aos eventos do processamento.

Cada reação é uma mudança de estado idempotente da mídia. Antes, qualquer
falha era só registrada no log: se o banco falhasse por um instante ao
marcar "texto pronto", o TextContentReady nunca saía, a análise nunca
começava e a mídia só falhava quando o prazo vencia. Agora a mudança é
repetida algumas vezes e, se ainda assim não for gravada, a mídia é dada
como falha, com o motivo, e o usuário é avisado.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, Sequence, TypeVar

import structlog

from src.media_management.application.ports import EventBusPort
from src.media_management.application.services.media_service import MediaService
from src.shared.domain.errors import ValidationError
from src.shared.domain.events import (
    AnalysisCompleted,
    AnalysisFailed,
    MediaFailed,
    MediaProcessingFailed,
    MediaProcessingStarted,
    TextContentReady,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.domain.value_objects.identifiers import MediaId, parse_media_id

logger = structlog.get_logger(__name__)

T = TypeVar("T")

RETRY_DELAYS_SECONDS = (0.5, 1.0, 2.0)
TEXT_NOT_RECORDED = "Não foi possível registrar o texto extraído. Tente reprocessar a mídia."
# O erro técnico da análise fica no log; a mídia mostra o que fazer.
ANALYSIS_FAILED = "A análise do conteúdo falhou. Tente reprocessar a mídia."


def _media_uuid(event) -> Optional[MediaId]:
    try:
        return parse_media_id(event.media_id)
    except ValidationError:
        logger.error("media_management.invalid_media_id", media_id=getattr(event, "media_id", None))
        return None


class MediaEventHandlers:
    """Atualiza o estado das mídias pelos casos de uso do MediaService."""

    def __init__(
        self,
        media_service: MediaService,
        event_bus: Optional[EventBusPort] = None,
        retry_delays: Sequence[float] = RETRY_DELAYS_SECONDS,
    ):
        self._media = media_service
        self._event_bus = event_bus
        self._retry_delays = tuple(retry_delays)

    async def handle_transcription_completed(self, event: TranscriptionCompleted) -> None:
        """Texto pronto: a mídia passa a "em análise" e o texto segue para a análise."""
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            media = await self._persist(lambda: self._media.record_text_ready(media_id), "text_ready", media_id)
        except Exception as exc:
            await self._give_up(event, media_id, exc)
            return
        if media is None or not self._event_bus:
            return
        await self._event_bus.publish(
            TextContentReady(
                media_id=str(media_id),
                transcription_id=str(event.transcription_id),
                text=event.text,
                user_id=event.user_id,
                filename=event.filename,
                language=event.language,
                correlation_id=event.correlation_id,
            )
        )
        logger.info("media_management.text_content_ready_published", media_id=str(media_id))

    async def handle_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Fim do pipeline: a mídia fica concluída (mesmo com etapas opcionais falhas)."""
        if not event.media_id:  # análise de texto avulso (/analyze), sem mídia
            return
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            await self._persist(lambda: self._media.record_analysis_completed(media_id), "completed", media_id)
        except Exception as exc:  # a análise está gravada; o prazo da análise marcará a mídia
            logger.error("media_management.completion_not_recorded", media_id=str(media_id), error=str(exc))

    async def handle_analysis_failed(self, event: AnalysisFailed) -> None:
        """A análise falhou de vez: a mídia falha e pode ser reprocessada.

        Antes, a mídia continuava "concluída" sem resumo e o reprocessamento,
        que só vale para mídias com falha, era recusado.
        """
        if not event.media_id:
            return
        logger.warning("media_management.analysis_failed", media_id=event.media_id, error=event.error_message)
        await self._fail(event, ANALYSIS_FAILED)

    async def handle_transcription_failed(self, event: TranscriptionFailed) -> None:
        await self._fail(event)

    async def handle_media_processing_failed(self, event: MediaProcessingFailed) -> None:
        await self._fail(event)

    async def handle_media_processing_started(self, event: MediaProcessingStarted) -> None:
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            await self._persist(lambda: self._media.record_processing_started(media_id), "started", media_id)
        except Exception as exc:  # só o rótulo "em processamento": o resultado ainda chega
            logger.error("media_management.processing_started_not_recorded", media_id=str(media_id), error=str(exc))

    async def _fail(self, event, message: Optional[str] = None) -> None:
        media_id = _media_uuid(event)
        if media_id is None:
            return
        reason = message or event.error_message
        try:
            await self._persist(
                lambda: self._media.record_processing_failed(media_id, reason), "failed", media_id
            )
        except Exception as exc:  # o prazo de processamento ainda marcará a falha
            logger.error("media_management.failure_not_recorded", media_id=str(media_id), error=str(exc))

    async def _give_up(self, event: TranscriptionCompleted, media_id: MediaId, cause: Exception) -> None:
        """O texto existe, mas a mídia não pôde ser concluída: falha visível,
        com motivo e aviso, em vez de esperar o prazo vencer."""
        logger.error("media_management.text_ready_not_recorded", media_id=str(media_id), error=str(cause))
        try:
            await self._persist(
                lambda: self._media.record_processing_failed(media_id, TEXT_NOT_RECORDED), "failed", media_id
            )
        except Exception as exc:
            logger.error("media_management.failure_not_recorded", media_id=str(media_id), error=str(exc))
        if self._event_bus:
            await self._event_bus.publish(
                MediaFailed(
                    media_id=str(media_id),
                    user_id=event.user_id,
                    stage="text_ready",
                    error_message=TEXT_NOT_RECORDED,
                    correlation_id=event.correlation_id,
                )
            )

    async def _persist(self, operation: Callable[[], Awaitable[T]], what: str, media_id: MediaId) -> T:
        """Executa a mudança de estado, repetindo-a se falhar (é idempotente)."""
        for delay in self._retry_delays:
            try:
                return await operation()
            except Exception as exc:
                logger.warning("media_management.state_retry", state=what, media_id=str(media_id), error=str(exc))
                await asyncio.sleep(delay)
        return await operation()
