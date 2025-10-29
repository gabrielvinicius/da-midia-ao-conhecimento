"""Event publication collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.media_management.domain.media import Media
from src.media_processing.tasks import process_media_task


class MediaEventPublisher(Protocol):
    """Publishes domain events produced by media commands."""

    async def publish_media_uploaded(self, media: Media, file_path: str) -> None:
        """Publish the media uploaded event."""


@dataclass
class DefaultMediaEventPublisher(MediaEventPublisher):
    """Default implementation that delegates to the event bus."""

    async def publish_media_uploaded(self, media: Media, file_path: str) -> None:
        # Replace event bus publication with Celery task scheduling.
        process_media_task.delay(media_id=str(media.id))
