"""Event handlers for Media Management domain events."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.shared.domain.enums import MediaStatus
from src.shared.domain.events import (
    MediaProcessingCompleted,
    MediaProcessingFailed,
    MediaProcessingStarted,
)

logger = structlog.get_logger(__name__)


class MediaStatusHandler:
    """Handles status updates based on processing events."""

    def __init__(self, media_repository: Any):
        self.media_repository = media_repository

    async def on_processing_started(self, event: MediaProcessingStarted) -> None:
        try:
            if hasattr(self.media_repository, "update_status"):
                self.media_repository.update_status(
                    UUID(event.media_id),
                    MediaStatus.PROCESSING,
                )
            logger.info(
                "media_status.updated",
                media_id=event.media_id,
                status="PROCESSING",
            )
        except Exception as exc:
            logger.error(
                "media_status.update_failed",
                media_id=event.media_id,
                error=str(exc),
            )

    async def on_processing_completed(self, event: MediaProcessingCompleted) -> None:
        try:
            if hasattr(self.media_repository, "update_status"):
                self.media_repository.update_status(
                    UUID(event.media_id),
                    MediaStatus.COMPLETED,
                )
            logger.info(
                "media_status.updated",
                media_id=event.media_id,
                status="COMPLETED",
            )
        except Exception as exc:
            logger.error(
                "media_status.update_failed",
                media_id=event.media_id,
                error=str(exc),
            )

    async def on_processing_failed(self, event: MediaProcessingFailed) -> None:
        try:
            if hasattr(self.media_repository, "update_status"):
                self.media_repository.update_status(
                    UUID(event.media_id),
                    MediaStatus.FAILED,
                    error_message=event.error_message,
                )
            logger.info(
                "media_status.updated",
                media_id=event.media_id,
                status="FAILED",
            )
        except Exception as exc:
            logger.error(
                "media_status.update_failed",
                media_id=event.media_id,
                error=str(exc),
            )
