from __future__ import annotations

from dataclasses import dataclass
import datetime
from typing import Any, Dict, List, Optional, Protocol, Set
from uuid import UUID

from src.media_management.domain import Media
from src.shared.application.observability import LoggerPort, MetricsPort



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


class RecoverableMediaPort(Protocol):
    async def list_waiting(self, created_before: datetime.datetime, limit: int = 50) -> List[Media]:
        """Mídias ainda enviadas ou em processamento, criadas antes do instante dado."""
        ...

    async def update(self, media: Media): ...


class ProcessingRecordsPort(Protocol):
    """Diz quais mídias já ganharam registro no processamento (transcrição ou extração)."""

    async def media_with_processing(self, media_ids: List[UUID]) -> Set[UUID]: ...


class StoredFileRemoverPort(Protocol):
    """Remove os arquivos de uma mídia do armazenamento (implementado pelo módulo storage)."""

    async def delete_folder(self, provider_name: str, folder_path: str) -> None: ...

    async def delete_file(self, provider_name: str, path: str) -> None: ...


class MediaDataEraserPort(Protocol):
    """Apaga o que um módulo derivou de uma mídia (transcrição, análise...).

    Cada módulo implementa a sua, sobre os próprios dados; este módulo só
    conhece a lista. Deve ser idempotente: uma exclusão interrompida pode ser
    repetida.
    """

    name: str

    async def erase(self, media_id: UUID) -> None: ...


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
