"""Base storage provider implementing shared behaviours."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.interfaces import StorageConfiguration, StorageProvider
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class BaseStorageProvider(StorageProvider, ABC):
    """Template base class for concrete storage providers."""

    def __init__(self, config: StorageConfiguration):
        super().__init__(config)

    async def upload(self, file_path: FilePath, content: bytes) -> FileMetadata:
        path = self._ensure_file_path(file_path)
        await self._do_write(path, content)
        metadata = await self.get_metadata(path)
        if metadata is None:
            metadata = FileMetadata(
                id=uuid4(),
                file_path=path,
                size=FileSize(len(content)),
                content_type="application/octet-stream",
                created_at=datetime.now(timezone.utc),
            )
        await self._post_write(path, metadata)
        return metadata

    async def download(self, file_path: FilePath) -> Optional[bytes]:
        path = self._ensure_file_path(file_path)
        return await self._do_read(path)

    async def delete(self, file_path: FilePath) -> bool:
        path = self._ensure_file_path(file_path)
        return await self._do_delete(path)

    def _ensure_file_path(self, file_path: FilePath | str) -> FilePath:
        if isinstance(file_path, FilePath):
            return file_path
        return FilePath.from_path(file_path)

    async def _post_write(self, file_path: FilePath, metadata: FileMetadata) -> None:
        """Hook executed after successful writes."""
        return None

    @abstractmethod
    async def _do_write(self, file_path: FilePath, content: bytes) -> None:
        ...

    @abstractmethod
    async def _do_read(self, file_path: FilePath) -> Optional[bytes]:
        ...

    @abstractmethod
    async def _do_delete(self, file_path: FilePath) -> bool:
        ...


__all__ = ["BaseStorageProvider"]
