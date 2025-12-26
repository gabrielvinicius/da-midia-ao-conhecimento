"""Event handlers for Media Management."""
from __future__ import annotations

import structlog
import uuid

from src.media_management.application.services.media_service import MediaService
from src.shared.domain.events import (
    MediaProcessingFailed,
    MediaProcessingStarted,
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
            try:
                media_id = uuid.UUID(str(event.media_id))
            except Exception:
                logger.error(
                    "media_management.invalid_media_id",
                    media_id=event.media_id,
                )
                return

            media = await self.media_service.media_repository.get_by_id(media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            # Domain logic: Mark as completed
            media.mark_as_completed()
            await self.media_service.media_repository.update(media)

            # Publish TextContentReady
            if self.media_service.event_bus:
                text_event = TextContentReady(
                    media_id=str(media_id),
                    transcription_id=str(event.transcription_id),
                    text_content=event.text_content,
                    user_id=event.user_id,
                    filename=event.metadata.get("filename")
                    if isinstance(event.metadata, dict)
                    else None,
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
            try:
                media_id = uuid.UUID(str(event.media_id))
            except Exception:
                logger.error(
                    "media_management.invalid_media_id",
                    media_id=event.media_id,
                )
                return

            media = await self.media_service.media_repository.get_by_id(media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            media.mark_as_failed(event.error_message or "Erro desconhecido")
            await self.media_service.media_repository.update(media)

        except Exception as exc:
            logger.error(
                "media_management.handle_transcription_failed_error",
                error=str(exc),
                media_id=event.media_id,
            )

    async def handle_media_processing_started(
        self, event: MediaProcessingStarted
    ) -> None:
        """Marca o Media como PROCESSING (ex.: início do OCR/text_extraction)."""
        logger.info(
            "media_management.handle_media_processing_started",
            media_id=event.media_id,
            stage=event.stage,
        )
        try:
            try:
                media_id = uuid.UUID(str(event.media_id))
            except Exception:
                logger.error(
                    "media_management.invalid_media_id",
                    media_id=event.media_id,
                )
                return

            media = await self.media_service.media_repository.get_by_id(media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            media.mark_as_processing()
            await self.media_service.media_repository.update(media)
        except Exception as exc:
            logger.error(
                "media_management.handle_media_processing_started_failed",
                error=str(exc),
                media_id=event.media_id,
                stage=event.stage,
            )

    async def handle_media_processing_failed(self, event: MediaProcessingFailed) -> None:
        """Marca o Media como FAILED (falha final de uma etapa de processamento)."""
        logger.info(
            "media_management.handle_media_processing_failed",
            media_id=event.media_id,
            stage=event.stage,
        )
        try:
            try:
                media_id = uuid.UUID(str(event.media_id))
            except Exception:
                logger.error(
                    "media_management.invalid_media_id",
                    media_id=event.media_id,
                )
                return

            media = await self.media_service.media_repository.get_by_id(media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            media.mark_as_failed(event.error_message or "Erro desconhecido")
            await self.media_service.media_repository.update(media)
        except Exception as exc:
            logger.error(
                "media_management.handle_media_processing_failed_error",
                error=str(exc),
                media_id=event.media_id,
                stage=event.stage,
            )

    async def handle_text_content_ready(self, event: TextContentReady) -> None:
        """Marca o Media como COMPLETED quando o texto final está disponível."""
        logger.info(
            "media_management.handle_text_content_ready",
            media_id=event.media_id,
        )
        try:
            try:
                media_id = uuid.UUID(str(event.media_id))
            except Exception:
                logger.error(
                    "media_management.invalid_media_id",
                    media_id=event.media_id,
                )
                return

            media = await self.media_service.media_repository.get_by_id(media_id)
            if not media:
                logger.error(
                    "media_management.media_not_found",
                    media_id=event.media_id,
                )
                return

            media.mark_as_completed()
            await self.media_service.media_repository.update(media)
        except Exception as exc:
            logger.error(
                "media_management.handle_text_content_ready_failed",
                error=str(exc),
                media_id=event.media_id,
            )
