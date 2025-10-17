# src/storage/domain/repositories/storage_repository.py
from abc import ABC, abstractmethod
from typing import Optional

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath


class StorageRepository(ABC):
    """Repository interface for storage operations (DIP compliance)."""
    
    @abstractmethod
    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file and return metadata."""
        pass
    
    @abstractmethod
    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content."""
        pass
    
    @abstractmethod
    async def remove(self, file_path: FilePath) -> bool:
        """Remove file. Returns True if removed, False if not found."""
        pass
    
    @abstractmethod
    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata without content."""
        pass