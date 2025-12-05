"""Simple local filesystem storage implementation used in tests."""
from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.repositories.storage_repository import StorageRepository
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class LocalStorageService(StorageRepository):
    """Persist files on the local filesystem using asynchronous wrappers."""

    def __init__(self, root_directory: Union[str, Path] = "storage") -> None:
        self._root = Path(root_directory)
        self._root.mkdir(parents=True, exist_ok=True)
        self._config = {"root_directory": str(root_directory)}

    @property
    def provider_name(self) -> str:
        return "local"

    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file and return metadata."""
        destination = self._resolve_path(file_path)
        
        try:
            await asyncio.to_thread(self._write_file, destination, content)
            
            # Create metadata
            stat = destination.stat()
            size = FileSize(stat.st_size)
            mime_type, _ = mimetypes.guess_type(destination)
            
            return FileMetadata(
                id=uuid4(),
                file_path=file_path,
                size=size,
                content_type=mime_type or "application/octet-stream",
                created_at=datetime.utcfromtimestamp(stat.st_ctime),
                updated_at=datetime.utcfromtimestamp(stat.st_mtime)
            )
        except Exception as exc:
            raise Exception(f"Failed to store file {file_path}: {exc}") from exc

    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content."""
        source = self._resolve_path(file_path)
        if not source.exists():
            return None
        try:
            return await asyncio.to_thread(source.read_bytes)
        except Exception as exc:
            raise Exception(f"Failed to retrieve file {file_path}: {exc}") from exc

    async def remove(self, file_path: FilePath) -> bool:
        """Remove file. Returns True if removed, False if not found."""
        target = self._resolve_path(file_path)
        if not target.exists():
            return False
        try:
            await asyncio.to_thread(target.unlink)
            return True
        except Exception as exc:
            raise Exception(f"Failed to remove file {file_path}: {exc}") from exc

    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        return self._resolve_path(file_path).exists()

    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata without content."""
        target = self._resolve_path(file_path)
        if not target.exists():
            return None
            
        try:
            stat = await asyncio.to_thread(target.stat)
            size = FileSize(stat.st_size)
            mime_type, _ = mimetypes.guess_type(target)
            
            return FileMetadata(
                id=uuid4(), # Local files don't have persistent IDs, generate one
                file_path=file_path,
                size=size,
                content_type=mime_type or "application/octet-stream",
                created_at=datetime.utcfromtimestamp(stat.st_ctime),
                updated_at=datetime.utcfromtimestamp(stat.st_mtime)
            )
        except Exception as exc:
             raise Exception(f"Failed to get metadata for {file_path}: {exc}") from exc

    async def list_files(self, prefix: str = "") -> List[str]:
        """Lists files in the local storage."""
        base_dir = self._root
        if prefix:
            base_dir = base_dir / prefix
        
        if not base_dir.exists():
            return []

        def _gather() -> List[str]:
            files = []
            for path in base_dir.rglob("*"):
                if path.is_file():
                    rel_path = path.relative_to(self._root).as_posix()
                    files.append(rel_path)
            return files

        try:
            return await asyncio.to_thread(_gather)
        except Exception as exc:
            raise Exception(f"Failed to list files: {exc}") from exc

    def _resolve_path(self, file_path: FilePath) -> Path:
        path = file_path.to_path()
        if path.is_absolute():
            # Security check: ensure it's within root if needed, 
            # but for now assuming trusted input or purely local
            return path
        return self._root / path

    @staticmethod
    def _write_file(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


__all__ = ["LocalStorageService"]

