"""Event publication collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import structlog

from src.media_management.domain.media import Media
from src.media_processing.tasks import process_media_task
from src.shared.events.bus import SupportsEventBus
from src.shared.events.domain_events import MediaUploaded

logger = structlog.get_logger(__name__)


class MediaEventPublisher(Protocol):
    """Publishes domain events produced by media commands."""

    async def publish_media_uploaded(self, media: Media, file_path: str) -> None:
        """Publish the media uploaded event."""


@dataclass
class DefaultMediaEventPublisher(MediaEventPublisher):
    """Default implementation that delegates to the event bus."""

    event_bus: SupportsEventBus | None = None
    emit_legacy_task: bool = True

    async def publish_media_uploaded(self, media: Media, file_path: str) -> None:
        if self.event_bus is not None:
            try:
                await self.event_bus.publish(
                    MediaUploaded(
                        media_id=str(media.id),
                        user_id=str(getattr(media, "user_id", "")),
                        storage_provider=getattr(media, "storage_provider", None),
                        filename=getattr(media, "filename", None),
                        file_path=file_path,
                        media_type=getattr(getattr(media, "media_type", None), "value", None)
                        if hasattr(getattr(media, "media_type", None), "value")
                        else getattr(media, "media_type", None),
                    )
                )
            except Exception as exc:  # pragma: no cover - fallback
                logger.warning("media.event_bus.publish_failed", error=str(exc))
        else:
            logger.debug("media.event_bus.missing", message="Event bus not configured; skipping publish")

        if self.emit_legacy_task:
            try:
                process_media_task.delay(media_id=str(media.id))
            except Exception as exc:  # pragma: no cover - Celery optional
                logger.warning("media.celery.enqueue_failed", error=str(exc))
