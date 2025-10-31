"""Side effect collaborators for media upload command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.media_management.domain.media import Media

from .event_publisher import MediaEventPublisher
from .metrics_publisher import MediaMetricsPublisher
from .upload_metadata_mapper import UploadMetadata


class MediaUploadSideEffectPublisher(Protocol):
    """Publishes side effects produced after a successful media upload."""

    async def publish(self, media: Media, metadata: UploadMetadata) -> None:
        """Publish the side effects related to a media upload."""


@dataclass(slots=True)
class DefaultMediaUploadSideEffectPublisher(MediaUploadSideEffectPublisher):
    """Default publisher that delegates to metrics and event publishers."""

    metrics_publisher: MediaMetricsPublisher
    event_publisher: MediaEventPublisher

    async def publish(self, media: Media, metadata: UploadMetadata) -> None:
        await self.metrics_publisher.publish(media, metadata.file_size)
        await self.event_publisher.publish_media_uploaded(media, metadata.stored_path)
