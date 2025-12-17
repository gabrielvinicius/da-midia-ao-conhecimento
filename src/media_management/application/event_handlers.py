"""Event handlers for Media Management."""
from __future__ import annotations

import structlog

from src.media_management.application.services.media_service import MediaService
from src.shared.domain.events import (
    TextContentReady,
    TranscriptionCompleted,
    TranscriptionFailed,
)

logger = structlog.get_logger(__name__)


class MediaEventHandlers:
    """Handles events updating Media state."""

    def __init__(self, media_service: MediaService):
        self.media_service = media_service

    async def handle_transcription_completed(
        self, event: TranscriptionCompleted
    ) -> None:
        """Update media status and publish TextContentReady."""
        logger.info(
            "media_management.handle_transcription_completed",
            media_id=event.media_id,
        )
        try:
            # Update status
            # We need to access the repository or a service method to update status.
            # MediaService doesn't explicitly have update_status but repository does.
            # Let's use repository directly via service (or add method to service).
            # Service is safer.
            media = await self.media_service.media_repository.get_by_id(event.media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            # Domain logic: Mark as completed
            updated_media = media.mark_completed()
            await self.media_service.media_repository.update(updated_media)

            # Publish TextContentReady
            if self.media_service.event_bus:
                text_event = TextContentReady(
                    media_id=str(event.media_id),
                    transcription_id=str(event.transcription_id),
                    text_content=event.text_content,
                    metadata=event.metadata,
                )
                await self.media_service.event_bus.publish(text_event)
                logger.info(
                    "media_management.text_content_ready_published",
                    media_id=event.media_id,
                )

        except Exception as exc:
            logger.error(
                "media_management.handle_transcription_completed_failed",
                error=str(exc),
                media_id=event.media_id,
            )

    async def handle_transcription_failed(self, event: TranscriptionFailed) -> None:
        """Update media status to FAILED."""
        logger.info(
            "media_management.handle_transcription_failed",
            media_id=event.media_id,
        )
        try:
            media = await self.media_service.media_repository.get_by_id(event.media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            updated_media = media.mark_failed(event.error_message)
            await self.media_service.media_repository.update(updated_media)

        except Exception as exc:
            logger.error(
                "media_management.handle_transcription_failed_error",
                error=str(exc),
                media_id=event.media_id,
            )
