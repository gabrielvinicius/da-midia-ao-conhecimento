# src/storage/infrastructure/providers/local_provider.py
"""Local filesystem storage provider - OCP and SRP compliance.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional
from uuid import uuid4

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.interfaces import StorageConfiguration
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize
from src.storage.infrastructure.providers.base_provider import BaseStorageProvider


class LocalStorageConfiguration(StorageConfiguration):
    """Configuration for local storage - SRP compliance."""

    def __init__(self, root_path: str = "storage"):
        self.root_path = Path(root_path)

    def get_config(self) -> dict[str, any]:
        """Get configuration dictionary."""
        return {"root_path": str(self.root_path)}

    def validate_config(self) -> bool:
        """Validate configuration."""
        try:
            self.root_path.mkdir(exist_ok=True, parents=True)
            return self.root_path.exists() and self.root_path.is_dir()
        except Exception:
            return False


class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage provider.
    Follows OCP - can be extended without modification.
    """

    def __init__(self, config: LocalStorageConfiguration):
        super().__init__(config)
        self._root = config.root_path
        self._root.mkdir(exist_ok=True, parents=True)

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "local"

    async def _do_write(self, file_path: FilePath, content: bytes) -> None:
        """Write file to local filesystem."""
        full_path = self._root / file_path.value
        await asyncio.to_thread(self._sync_write, full_path, content)

    def _sync_write(self, path: Path, content: bytes) -> None:
        """Synchronous write operation."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def _do_read(self, file_path: FilePath) -> Optional[bytes]:
        """Read file from local filesystem."""
        full_path = self._root / file_path.value
        try:
            return await asyncio.to_thread(self._sync_read, full_path)
        except FileNotFoundError:
            return None

    def _sync_read(self, path: Path) -> bytes:
        """Synchronous read operation."""
        return path.read_bytes()

    async def _do_delete(self, file_path: FilePath) -> bool:
        """Delete file from local filesystem."""
        full_path = self._root / file_path.value
        try:
            return await asyncio.to_thread(self._sync_delete, full_path)
        except FileNotFoundError:
            return False

    def _sync_delete(self, path: Path) -> bool:
        """Synchronous delete operation."""
        if path.exists():
            path.unlink()
            return True
        return False

    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        full_path = self._root / file_path.value
        return await asyncio.to_thread(full_path.exists)

    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata."""
        full_path = self._root / file_path.value
        try:
            stat = await asyncio.to_thread(full_path.stat)
            return FileMetadata(
                id=uuid4(),  # In real implementation, should be persisted
                file_path=file_path,
                size=FileSize(stat.st_size),
                content_type="application/octet-stream",
                created_at=datetime.fromtimestamp(stat.st_ctime)
            )
        except FileNotFoundError:
            return None

    async def list_files(self, prefix: Optional[str] = None) -> AsyncIterator[FilePath]:
        """List files with optional prefix filter."""
        search_path = self._root
        if prefix:
            search_path = self._root / prefix

        try:
            files = await asyncio.to_thread(self._sync_list_files, search_path, prefix)
            for file_path in files:
                yield FilePath.from_path(file_path)
        except FileNotFoundError:
            return

    def _sync_list_files(self, search_path: Path, prefix: Optional[str]) -> list[str]:
        """Synchronous file listing."""
        files = []
        if search_path.is_dir():
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self._root)
                    if not prefix or str(relative_path).startswith(prefix):
                        files.append(str(relative_path))
        return files

    async def _post_write(self, file_path: FilePath, metadata: FileMetadata) -> None:
        """Hook for post-write operations."""
        # Could add checksums, backups, etc.
        pass
