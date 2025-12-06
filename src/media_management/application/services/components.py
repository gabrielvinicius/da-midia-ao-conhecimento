"""Components for Media Service operations.

Contains helper classes for uploading, validating, and side-effects.
"""

from __future__ import annotations

import abc
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from src.media_management.application.commands.dto import CreateMediaCommand
from src.media_management.domain.media import Media
from src.shared.domain.errors import ValidationError
from src.shared.domain.events import MediaUploaded
from src.shared.domain.enums import MediaStatus
from src.shared.infrastructure.event_bus import SupportsEventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


@dataclass
class UploadResult:
    """Result of a storage upload operation."""
    destination_path: str
    metadata: Dict[str, Any]


@dataclass
class UploadMetadata:
    """Standardized metadata from an upload."""
    stored_path: str
    file_size: int
    hash_digest: Optional[str] = None


# --- Interfaces ---

class StorageUploader(abc.ABC):
    """Abstract base for storage upload strategies."""
    
    @abc.abstractmethod
    async def upload(
        self, command: CreateMediaCommand, media_id: uuid.UUID, content_type: str
    ) -> UploadResult:
        """Uploads file content to storage."""
        pass


class UploadMetadataMapper(abc.ABC):
    """Abstract base for mapping storage metadata to domain values."""

    @abc.abstractmethod
    def map(
        self,
        storage_metadata: Dict[str, Any],
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata:
        """Maps storage response to UploadMetadata."""
        pass


class MediaUploadSideEffectPublisher(abc.ABC):
    """Abstract base for publishing side effects after upload."""

    @abc.abstractmethod
    async def publish(self, media: Media, metadata: UploadMetadata) -> None:
        """Publishes events and metrics."""
        pass


class MediaFileValidator(abc.ABC):
    """Abstract base for file validation."""

    @abc.abstractmethod
    def validate(self, file_content: bytes, filename: str) -> None:
        """Validates file content and name."""
        pass


# --- Implementations ---

class DefaultStorageServiceResolver:
    """Resolves the storage service to use."""
    
    def __init__(self, factory: StorageServiceFactory):
        self.factory = factory

    def resolve(self, provider_name: Optional[str]):
        provider = (provider_name or "local").lower()
        return self.factory.create_storage_service(provider)


class DefaultStorageUploader(StorageUploader):
    """Standard implementation of storage uploading."""

    def __init__(self, storage_resolver: DefaultStorageServiceResolver):
        self.resolver = storage_resolver

    async def upload(
        self, command: CreateMediaCommand, media_id: uuid.UUID, content_type: str
    ) -> UploadResult:
        storage_service = self.resolver.resolve(command.storage_provider)
        
        # Generate a safe path: {user_id}/{year}/{month}/{media_id}/{filename}
        now = datetime.now(timezone.utc)
        safe_filename = os.path.basename(command.filename)
        destination_path = (
            f"{command.user_id}/{now.year}/{now.month:02d}/{media_id}/{safe_filename}"
        )

        metadata = await storage_service.upload(
            file_data=command.file,
            destination=destination_path,
            content_type=content_type
        )
        
        return UploadResult(destination_path=destination_path, metadata=metadata)


class DefaultUploadMetadataMapper(UploadMetadataMapper):
    """Standard implementation of metadata mapping."""

    def map(
        self,
        storage_metadata: Dict[str, Any],
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata:
        # Try to extract size from metadata, fallback to len(file_data)
        size = storage_metadata.get("size") or len(file_data)
        path = storage_metadata.get("path") or default_path
        
        return UploadMetadata(
            stored_path=path,
            file_size=size,
            hash_digest=storage_metadata.get("etag") or storage_metadata.get("hash"),
        )


class DefaultMediaMetricsPublisher:
    """Helper for publishing metrics."""
    
    def __init__(self, metrics_service: Any):
        self.metrics = metrics_service

    async def record_upload(self, media: Media, size: int, duration: float, status: str):
        if hasattr(self.metrics, "record_operation"):
            await self.metrics.record_operation(
                operation="create_media",
                user_id=str(media.user_id),
                status=status,
                duration=duration,
                media_id=str(media.id),
                media_type=media.media_type.value if hasattr(media.media_type, "value") else media.media_type,
                provider=media.storage_provider
            )


class DefaultMediaEventPublisher:
    """Helper for publishing events."""

    def __init__(self, event_bus: Optional[SupportsEventBus], emit_legacy_task: bool):
        self.event_bus = event_bus
        self.emit_legacy_task = emit_legacy_task

    async def publish_uploaded(self, media: Media, metadata: UploadMetadata):
        if not self.event_bus:
            return

        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(media.user_id),
            filename=media.filename,
            storage_provider=media.storage_provider,
            media_type=media.media_type.value if hasattr(media.media_type, "value") else media.media_type,
            file_size_bytes=metadata.file_size,
            transcription_provider=media.transcription_provider,
            summarization_provider=media.summarization_provider,
            sentiment_provider=media.sentiment_provider,
            topic_modeling_provider=media.topic_modeling_provider,
            language=media.language,
            correlation_id=f"upload-{uuid.uuid4()}",
        )
        await self.event_bus.publish(event)


class DefaultMediaUploadSideEffectPublisher(MediaUploadSideEffectPublisher):
    """Orchestrates metrics and events after upload."""

    def __init__(
        self,
        metrics_publisher: DefaultMediaMetricsPublisher,
        event_publisher: DefaultMediaEventPublisher,
    ):
        self.metrics = metrics_publisher
        self.events = event_publisher

    async def publish(self, media: Media, metadata: UploadMetadata) -> None:
        # We don't have the start time here easily, assuming 0 for now or refactor to pass it
        # In a real scenario, we'd pass the duration.
        await self.metrics.record_upload(media, metadata.file_size, 0.0, "success")
        await self.events.publish_uploaded(media, metadata)


class FileSizeMediaFileValidator(MediaFileValidator):
    """Validates file size constraints."""

    def __init__(self, min_size_bytes: int, max_size_bytes: int):
        self.min = min_size_bytes
        self.max = max_size_bytes

    def validate(self, file_content: bytes, filename: str) -> None:
        size = len(file_content)
        if size < self.min:
            raise ValidationError("file", filename, f"File is too small (min {self.min} bytes)")
        if size > self.max:
            raise ValidationError("file", filename, f"File is too large (max {self.max} bytes)")
