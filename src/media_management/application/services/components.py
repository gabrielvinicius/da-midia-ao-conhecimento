"""Supporting components for the MediaService.

These classes stay lightweight but fully functional: they publish events,
record metrics, and perform basic file validation without pulling concrete
infrastructure dependencies into the application layer.
"""

from __future__ import annotations

import structlog

from src.media_management.application.ports import (
    EventBusPort,
    MediaMetricsPort,
    StorageUploaderPort,
    UploadMetadata,
    UploadMetadataMapperPort,
    UploadResult,
)
from src.shared.domain.errors import ValidationError
from src.shared.domain.events import (
    MediaDeleted,
    MediaReprocessRequested,
    MediaUploaded,
)

logger = structlog.get_logger(__name__)


class MediaFileValidator:
    """Protocol-like base class for validators."""

    def validate(
        self,
        file_data: bytes,
        filename: str,
    ) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class FileSizeMediaFileValidator(MediaFileValidator):
    """Validates that the uploaded file is within the configured size bounds."""

    def __init__(self, min_size_bytes: int, max_size_bytes: int) -> None:
        self._min = min_size_bytes
        self._max = max_size_bytes

    def validate(self, file_data: bytes, filename: str) -> None:
        size = len(file_data) if hasattr(file_data, "__len__") else 0
        if size < self._min:
            raise ValidationError(
                "file",
                filename,
                f"File too small (min {self._min} bytes)",
            )
        if size > self._max:
            raise ValidationError(
                "file",
                filename,
                f"File too large (max {self._max} bytes)",
            )


class MediaMetricsPublisher:
    """Publishes upload metrics using the configured metrics port."""

    def __init__(self, metrics_service: MediaMetricsPort | None) -> None:
        self._metrics = metrics_service

    async def publish(self, *, media, upload_metadata: UploadMetadata) -> None:
        if not self._metrics:
            return
        try:
            await self._metrics.record_operation(
                operation="create_media",
                duration=0.0,
                success=True,
                media_id=str(media.id),
                media_type=getattr(media.media_type, "value", None)
                or str(media.media_type),
                provider=media.storage_provider,
                user_id=str(media.user_id),
                status="success",
            )
        except Exception:  # pragma: no cover - defensive
            logger.warning("media_management.metrics.publish_failed")


class MediaEventPublisher:
    """Publishes domain events to the event bus."""

    def __init__(
        self,
        event_bus: EventBusPort | None,
    ) -> None:
        self._event_bus = event_bus

    async def publish_uploaded(self, *, media, upload_metadata: UploadMetadata) -> None:
        if not self._event_bus:
            return
        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(media.user_id),
            media_type=getattr(media.media_type, "value", None)
            or str(media.media_type),
            storage_provider=media.storage_provider,
            transcription_provider=media.transcription_provider,
            summarization_provider=media.summarization_provider,
            sentiment_provider=media.sentiment_provider,
            topic_modeling_provider=media.topic_modeling_provider,
            file_path=upload_metadata.stored_path,
            file_size_bytes=upload_metadata.file_size,
            language=getattr(media, "language", None),
            filename=media.filename,
        )
        await self._event_bus.publish(event)

    async def publish_deleted(self, *, media, triggered_by: str, actor_id: str) -> None:
        if not self._event_bus:
            return
        event = MediaDeleted(
            media_id=str(media.id),
            user_id=str(media.user_id),
            triggered_by=triggered_by,
            actor_id=actor_id,
        )
        await self._event_bus.publish(event)

    async def publish_reprocess_requested(
        self, *, media, triggered_by: str, actor_id: str
    ) -> None:
        if not self._event_bus:
            return
        event = MediaReprocessRequested(
            media_id=str(media.id),
            triggered_by=triggered_by,
            actor_id=actor_id,
        )
        await self._event_bus.publish(event)


class MediaUploadSideEffectPublisher:
    """Orchestrates the side-effects triggered after a successful upload."""

    async def publish(self, media, upload_metadata: UploadMetadata) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class DefaultMediaUploadSideEffectPublisher(MediaUploadSideEffectPublisher):
    def __init__(
        self,
        metrics_publisher: MediaMetricsPublisher,
        event_publisher: MediaEventPublisher,
    ) -> None:
        self.metrics_publisher = metrics_publisher
        self.event_publisher = event_publisher

    async def publish(self, media, upload_metadata: UploadMetadata) -> None:
        await self.metrics_publisher.publish(
            media=media,
            upload_metadata=upload_metadata,
        )
        await self.event_publisher.publish_uploaded(
            media=media,
            upload_metadata=upload_metadata,
        )


__all__ = [
    # Upload helpers
    "UploadResult",
    "UploadMetadata",
    "StorageUploaderPort",
    "UploadMetadataMapperPort",
    # Validators
    "MediaFileValidator",
    "FileSizeMediaFileValidator",
    # Publishers
    "MediaMetricsPublisher",
    "MediaEventPublisher",
    "MediaUploadSideEffectPublisher",
    "DefaultMediaUploadSideEffectPublisher",
]
