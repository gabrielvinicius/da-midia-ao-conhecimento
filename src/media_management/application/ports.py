from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol
from uuid import UUID

from src.media_management.domain import Media
from src.shared.infrastructure.observability.ports import LoggerPort, MetricsPort
from src.storage.application.ports import FileStoragePort

StorageUploadPort = FileStoragePort


class MediaMetricsPort(MetricsPort, Protocol):
    ...


class MediaLoggerPort(LoggerPort, Protocol):
    ...


class EventBusPort(Protocol):
    async def publish(self, event: Any) -> None: ...


class MediaRepositoryPort(Protocol):
    async def get_by_id(self, media_id: UUID): ...
    async def save(self, media: Media): ...
    async def delete(self, media_id: UUID): ...
    async def update(self, media: Media): ...
    async def count_all(self) -> int: ...
    async def count_by_user(self, user_id: UUID) -> int: ...
    async def count_by_status(self, status): ...
    async def count_by_user_and_status(self, user_id: UUID, status): ...
    async def count_by_type(self, media_type): ...
    async def count_by_user_and_type(self, user_id: UUID, media_type): ...
    async def count_filtered(
        self,
        *,
        user_id: UUID | None = None,
        status: Any | None = None,
        search: str | None = None,
    ) -> int: ...
    async def list_paginated(
        self,
        page: int,
        limit: int,
        user_id: UUID | None = None,
        status: Any | None = None,
        search: str | None = None,
        order: str = "desc",
    ): ...


class TranscriptionCleanupPort(Protocol):
    async def delete_by_media_id(self, media_id: UUID) -> None: ...


@dataclass
class UploadResult:
    destination_path: str
    metadata: Dict[str, Any]


@dataclass
class UploadMetadata:
    stored_path: str
    file_size: int
    hash_digest: Optional[str] = None


class StorageUploaderPort(Protocol):
    async def upload(
        self, command, media_id: UUID, content_type: str
    ) -> UploadResult: ...


class StorageDownloaderPort(Protocol):
    async def download(self, provider_name: str, path: str) -> bytes: ...


class UploadMetadataMapperPort(Protocol):
    def map(
        self,
        storage_metadata: Dict[str, Any],
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata: ...
