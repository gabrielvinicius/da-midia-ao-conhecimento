"""Metrics publication collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.media_management.domain.enums import MediaType
from src.media_management.domain.media import Media


class MediaMetricsPublisher(Protocol):
    """Records metrics for media command execution."""

    async def publish(self, media: Media, file_size: int) -> None:
        """Publish metrics related to the media upload."""


@dataclass
class DefaultMediaMetricsPublisher(MediaMetricsPublisher):
    """Default implementation using the configured metrics service."""

    metrics_service: Any

    async def publish(self, media: Media, file_size: int) -> None:
        service = self.metrics_service

        if hasattr(service, "increment_counter"):
            service.increment_counter(
                "media_uploads_total",
                media_type=media.media_type.value if isinstance(media.media_type, MediaType) else media.media_type,
                storage_provider=media.storage_provider,
            )

        if hasattr(service, "record_histogram"):
            service.record_histogram(
                "media_upload_file_size_bytes",
                file_size,
                media_type=media.media_type.value if isinstance(media.media_type, MediaType) else media.media_type,
            )
