"""Event publication collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.media_management.domain.media import Media
from src.shared.events.domain_events import MediaUploaded


class MediaEventPublisher(Protocol):
    """Publishes domain events produced by media commands."""

    async def publish_media_uploaded(self, media: Media, file_path: str) -> None:
        """Publish the media uploaded event."""


@dataclass
class DefaultMediaEventPublisher(MediaEventPublisher):
    """Default implementation that delegates to the event bus."""

    event_bus: Any

    async def publish_media_uploaded(self, media: Media, file_path: str) -> None:
        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(getattr(media, "user_id", "")),
            media_type=media.media_type,
            file_path=file_path,
            storage_provider=media.storage_provider,
            transcription_provider=getattr(media, "transcription_provider", None),
            summarization_provider=getattr(media, "summarization_provider", None),
        )
        await self.event_bus.publish(event)
