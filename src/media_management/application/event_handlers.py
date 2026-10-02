"""Reações do módulo de mídias aos eventos do processamento."""
from __future__ import annotations

from typing import Optional

import structlog

from src.media_management.application.ports import EventBusPort
from src.media_management.application.services.media_service import MediaService
from src.shared.domain.events import (
    MediaProcessingFailed,
    MediaProcessingStarted,
    TextContentReady,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.domain.errors import ValidationError
from src.shared.domain.value_objects.identifiers import MediaId, parse_media_id

logger = structlog.get_logger(__name__)


def _media_uuid(event) -> Optional[MediaId]:
    try:
        return parse_media_id(event.media_id)
    except ValidationError:
        logger.error("media_management.invalid_media_id", media_id=getattr(event, "media_id", None))
        return None


class MediaEventHandlers:
    """Atualiza o estado das mídias pelos casos de uso do MediaService."""

    def __init__(self, media_service: MediaService, event_bus: Optional[EventBusPort] = None):
        self._media = media_service
        self._event_bus = event_bus

    async def handle_transcription_completed(self, event: TranscriptionCompleted) -> None:
        """Conclui a mídia e avisa que o texto está pronto para a análise."""
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            media = await self._media.record_text_ready(media_id)
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
        except Exception as exc:
            logger.error(
                "media_management.handle_transcription_completed_failed",
                error=str(exc),
                media_id=str(media_id),
            )

    async def handle_transcription_failed(self, event: TranscriptionFailed) -> None:
        await self._fail(event, "handle_transcription_failed")

    async def handle_media_processing_failed(self, event: MediaProcessingFailed) -> None:
        await self._fail(event, "handle_media_processing_failed")

    async def handle_media_processing_started(self, event: MediaProcessingStarted) -> None:
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            await self._media.record_processing_started(media_id)
        except Exception as exc:
            logger.error(
                "media_management.handle_media_processing_started_failed",
                error=str(exc),
                media_id=str(media_id),
                stage=event.stage,
            )

    async def handle_text_content_ready(self, event: TextContentReady) -> None:
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            await self._media.record_text_ready(media_id)
        except Exception as exc:
            logger.error(
                "media_management.handle_text_content_ready_failed",
                error=str(exc),
                media_id=str(media_id),
            )

    async def _fail(self, event, handler: str) -> None:
        media_id = _media_uuid(event)
        if media_id is None:
            return
        try:
            await self._media.record_processing_failed(media_id, event.error_message)
        except Exception as exc:
            logger.error(f"media_management.{handler}_error", error=str(exc), media_id=str(media_id))
