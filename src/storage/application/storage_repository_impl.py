# src/storage/application/storage_repository_impl.py
"""
Storage repository implementation - DIP compliance.
"""
from typing import Optional

from src.storage.domain.interfaces import StorageRepository
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.services.file_validator import FileValidator
from src.storage.domain.services.storage_coordinator import StorageCoordinator


class StorageRepositoryImpl(StorageRepository):
    """
    High-level storage repository implementation.
    Follows DIP - depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        storage_coordinator: StorageCoordinator,
        file_validator: FileValidator
    ):
        self._coordinator = storage_coordinator
        self._validator = file_validator
    
    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file with validation and coordination."""
        # Domain validation
        self._validator.validate_path(file_path)
        
        # Delegate to coordinator for actual storage
        return await self._coordinator.store_file(file_path, content)
    
    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content."""
        return await self._coordinator.retrieve_file(file_path)
    
    async def remove(self, file_path: FilePath) -> bool:
        """Remove file."""
        return await self._coordinator.delete_file(file_path)
    
    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        # Delegate to provider through coordinator
        return await self._coordinator._provider.exists(file_path)
    
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata."""
        # Delegate to provider through coordinator
        return await self._coordinator._provider.get_metadata(file_path)
