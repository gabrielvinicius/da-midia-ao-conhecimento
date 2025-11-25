"""Minimal component implementations used by `CreateMediaCommandHandler`.

The original project expunha uma série de helpers (uploader, validadores,
publicadores de métricas/eventos). O handler ainda depende dessas classes para
manter compatibilidade com pipelines existentes (Celery/worker). Esta versão
mantém apenas o comportamento necessário para salvar arquivos e disparar
eventos/ métricas quando disponíveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.shared.events.domain_events import MediaUploaded
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StorageUploadResult:
    destination_path: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class UploadMetadata:
    stored_path: str
    file_size: int


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


class DefaultStorageServiceResolver:
    """Resolve storage adapters using the configured factory."""

    def __init__(self, factory: Any) -> None:
        self._factory = factory

    def resolve(self, provider: str):
        try:
            return self._factory.create_storage_service(provider)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("media.components.storage_resolver_failed", provider=provider, error=str(exc))
            raise


class DefaultStorageUploader:
    """Upload helper that stores the blob and returns metadata."""

    def __init__(self, storage_resolver: DefaultStorageServiceResolver) -> None:
        self._resolver = storage_resolver

    async def upload(
        self,
        *,
        command: Any,
        media_id: UUID,
        content_type: str,
    ) -> StorageUploadResult:
        storage_client = self._resolver.resolve(command.storage_provider)
        destination_path = f"media/{command.user_id}/{media_id}/{command.filename}"
        metadata = await storage_client.upload(
            destination_path=destination_path,
            content=command.file,
            filename=command.filename,
            content_type=content_type,
            metadata=command.metadata or {},
        )
        metadata_dict = metadata or {}
        return StorageUploadResult(destination_path=destination_path, metadata=metadata_dict)


# ---------------------------------------------------------------------------
# Metadata mapper
# ---------------------------------------------------------------------------


class DefaultUploadMetadataMapper:
    def map(
        self,
        metadata: Optional[Dict[str, Any]],
        *,
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata:
        stored_path = (metadata or {}).get("path") or default_path
        size = (metadata or {}).get("size") or len(file_data or b"")
        return UploadMetadata(stored_path=stored_path, file_size=size)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class MediaFileValidator:
    def validate(self, _file: bytes, _filename: str) -> None:
        return None


class FileSizeMediaFileValidator(MediaFileValidator):
    def __init__(self, *, min_size_bytes: int, max_size_bytes: int) -> None:
        self._min = min_size_bytes
        self._max = max_size_bytes

    def validate(self, file_data: bytes, filename: str) -> None:
        size = len(file_data or b"")
        if size < self._min:
            raise ValidationError("file", filename, "File is empty")
        if size > self._max:
            raise ValidationError("file", filename, "File exceeds size limit")


# ---------------------------------------------------------------------------
# Publishing side effects
# ---------------------------------------------------------------------------


class DefaultMediaMetricsPublisher:
    def __init__(self, *, metrics_service: Any) -> None:
        self._metrics = metrics_service

    async def publish(self, media: Any, metadata: UploadMetadata) -> None:
        if self._metrics is None:
            return
        record = getattr(self._metrics, "record_operation", None)
        if record is None:
            return
        try:
            await record(
                operation="media_upload",
                media_type=getattr(media.media_type, "value", str(media.media_type)),
                storage_provider=getattr(media, "storage_provider", None),
                file_size=metadata.file_size,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("media.components.metrics_failed", error=str(exc))


class DefaultMediaEventPublisher:
    def __init__(self, *, event_bus: Any, emit_legacy_task: bool = True) -> None:
        self._event_bus = event_bus
        self._emit_legacy_task = emit_legacy_task

    async def publish(self, media: Any, metadata: UploadMetadata) -> None:
        if not self._event_bus or not self._emit_legacy_task:
            return
        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(media.user_id),
            filename=getattr(media, "filename", None),
            storage_provider=getattr(media, "storage_provider", None),
            media_type=getattr(media.media_type, "value", str(media.media_type)),
            file_size=metadata.file_size,
        )
        try:
            await self._event_bus.publish(event)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("media.components.event_publish_failed", error=str(exc))


class DefaultMediaUploadSideEffectPublisher:
    def __init__(self, *, metrics_publisher: Any, event_publisher: Any) -> None:
        self._metrics_publisher = metrics_publisher
        self._event_publisher = event_publisher

    async def publish(self, media: Any, metadata: UploadMetadata) -> None:
        await self._metrics_publisher.publish(media, metadata)
        await self._event_publisher.publish(media, metadata)


# Aliases exported for compatibility
StorageUploader = DefaultStorageUploader
UploadMetadataMapper = DefaultUploadMetadataMapper
MediaUploadSideEffectPublisher = DefaultMediaUploadSideEffectPublisher

