"""Event handlers for Media Management domain events."""
from __future__ import annotations

import structlog
from uuid import UUID

from src.media_management.domain.enums import MediaStatus
from src.shared.events.domain_events import (
    MediaProcessingCompleted,
    MediaProcessingFailed,
    MediaProcessingStarted,
)

logger = structlog.get_logger(__name__)


class MediaStatusHandler:
    """Handles status updates based on processing events."""

    def __init__(self, media_repository: Any):
        # Supports both Sync and Async repositories ideally, but for Worker context we use Sync.
        # Using Any to avoid strict type check issues between Sync/Async repos in this context.
        self.media_repository = media_repository

    async def on_processing_started(self, event: MediaProcessingStarted) -> None:
        try:
            # If repository is sync, we might need to wrap in asyncio.to_thread if running in loop,
            # but if the event bus awaits it, and we are in a sync-to-async bridge, it depends.
            # For simplicity in this architecture, we assume the repository method matches the context
            # or we use a sync-compatible check.
            
            # However, EventBus awaits handlers. So this must be async def.
            # If self.media_repository is MediaRepositorySync, it blocks.
            # Blocking in async handler is bad for concurrency but fine for a linear worker task.
            
            if hasattr(self.media_repository, "update_status"):
                # Call sync method directly
                self.media_repository.update_status(
                    UUID(event.media_id),
                    MediaStatus.PROCESSING,
                )
            logger.info("media_status.updated", media_id=event.media_id, status="PROCESSING")
        except Exception as exc:
            logger.error("media_status.update_failed", media_id=event.media_id, error=str(exc))

    async def on_processing_completed(self, event: MediaProcessingCompleted) -> None:
        try:
            if hasattr(self.media_repository, "update_status"):
                self.media_repository.update_status(
                    UUID(event.media_id),
                    MediaStatus.COMPLETED,
                )
            logger.info("media_status.updated", media_id=event.media_id, status="COMPLETED")
        except Exception as exc:
            logger.error("media_status.update_failed", media_id=event.media_id, error=str(exc))

    async def on_processing_failed(self, event: MediaProcessingFailed) -> None:
        try:
            if hasattr(self.media_repository, "update_status"):
                self.media_repository.update_status(
                    UUID(event.media_id),
                    MediaStatus.FAILED,
                    error_message=event.error_message,
                )
            logger.info("media_status.updated", media_id=event.media_id, status="FAILED")
        except Exception as exc:
            logger.error("media_status.update_failed", media_id=event.media_id, error=str(exc))
