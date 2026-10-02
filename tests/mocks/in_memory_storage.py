# tests/mocks/in_memory_storage.py
"""Enhanced in-memory storage service for comprehensive testing.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from src.storage.application.ports import StorageRepositoryPort
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class InMemoryStorage(StorageRepositoryPort):
    """Enhanced in-memory storage with testing utilities."""

    def __init__(self):
        self.files: Dict[str, bytes] = {}
        self.metadata: Dict[str, FileMetadata] = {}
        self.upload_count = 0
        self.download_count = 0

    @property
    def provider_name(self) -> str:
        return "in-memory"

    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file content in memory."""
        self.upload_count += 1
        path_str = str(file_path)
        self.files[path_str] = content

        meta = FileMetadata(
            id=uuid4(),
            file_path=file_path,
            size=FileSize(len(content)),
            content_type="application/octet-stream",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.metadata[path_str] = meta
        return meta

    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content from memory."""
        self.download_count += 1
        path_str = str(file_path)
        return self.files.get(path_str)

    async def read_range(self, file_path: FilePath, start: int, end: int) -> Optional[bytes]:
        data = self.files.get(str(file_path))
        return None if data is None else data[start : end + 1]

    async def download_to(self, file_path: FilePath, destination: str) -> bool:
        data = await self.retrieve(file_path)
        if data is None:
            return False
        with open(destination, "wb") as target:
            target.write(data)
        return True

    async def remove(self, file_path: FilePath) -> bool:
        """Remove file from memory storage."""
        path_str = str(file_path)
        if path_str in self.files:
            del self.files[path_str]
            if path_str in self.metadata:
                del self.metadata[path_str]
            return True
        return False

    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists in memory storage."""
        return str(file_path) in self.files

    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        return self.metadata.get(str(file_path))

    async def list_files(self, prefix: str = "") -> List[str]:
        return [f for f in self.files.keys() if f.startswith(prefix)]

    # Compatibility methods for tests calling old methods directly (if any)
    async def upload(self, file_path: str, file: bytes) -> None:
        await self.store(FilePath.from_path(file_path), file)

    async def download(self, file_path: str) -> Optional[Tuple[bytes, str]]:
        content = await self.retrieve(FilePath.from_path(file_path))
        if content:
            return content, file_path.split("/")[-1]
        return None

    async def delete(self, file_path: str) -> bool:
        return await self.remove(FilePath.from_path(file_path))

    def clear(self):
        """Clear all stored files (useful for test cleanup)."""
        self.files.clear()
        self.metadata.clear()
        self.upload_count = 0
        self.download_count = 0

    def get_stats(self) -> dict:
        """Get storage statistics for testing."""
        return {
            "files_count": len(self.files),
            "total_size": sum(len(content) for content in self.files.values()),
            "upload_count": self.upload_count,
            "download_count": self.download_count
        }

