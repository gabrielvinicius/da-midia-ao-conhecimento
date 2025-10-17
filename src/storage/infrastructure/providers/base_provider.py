# src/storage/infrastructure/providers/base_provider.py
"""
Base implementation for storage providers - Template Method pattern.
"""
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator, Dict, Any
from datetime import datetime
from uuid import uuid4

from src.storage.domain.interfaces import StorageProvider, StorageConfiguration
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class StorageProviderError(Exception):
    """Base exception for storage provider errors."""
    pass


class BaseStorageProvider(StorageProvider):
    """
    Base storage provider implementing common functionality.
    Follows Template Method pattern and OCP.
    """
    
    def __init__(self, config: StorageConfiguration):
        self._config = config
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate provider configuration."""
        if not self._config.validate_config():
            raise StorageProviderError("Invalid storage configuration")
    
    async def write(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Template method for writing files."""
        try:
            # Pre-write hook
            await self._pre_write(file_path, content)
            
            # Actual write operation (implemented by subclasses)
            await self._do_write(file_path, content)
            
            # Create metadata
            metadata = self._create_metadata(file_path, content)
            
            # Post-write hook
            await self._post_write(file_path, metadata)
            
            return metadata
            
        except Exception as e:
            await self._handle_write_error(file_path, e)
            raise StorageProviderError(f"Write failed for {file_path}") from e
    
    async def read(self, file_path: FilePath) -> Optional[bytes]:
        """Template method for reading files."""
        try:
            # Pre-read hook
            await self._pre_read(file_path)
            
            # Actual read operation (implemented by subclasses)
            content = await self._do_read(file_path)
            
            # Post-read hook
            await self._post_read(file_path, content)
            
            return content
            
        except Exception as e:
            await self._handle_read_error(file_path, e)
            raise StorageProviderError(f"Read failed for {file_path}") from e
    
    async def delete(self, file_path: FilePath) -> bool:
        """Template method for deleting files."""
        try:
            # Pre-delete hook
            await self._pre_delete(file_path)
            
            # Actual delete operation (implemented by subclasses)
            result = await self._do_delete(file_path)
            
            # Post-delete hook
            await self._post_delete(file_path, result)
            
            return result
            
        except Exception as e:
            await self._handle_delete_error(file_path, e)
            raise StorageProviderError(f"Delete failed for {file_path}") from e
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _do_write(self, file_path: FilePath, content: bytes) -> None:
        """Actual write implementation."""
        pass
    
    @abstractmethod
    async def _do_read(self, file_path: FilePath) -> Optional[bytes]:
        """Actual read implementation."""
        pass
    
    @abstractmethod
    async def _do_delete(self, file_path: FilePath) -> bool:
        """Actual delete implementation."""
        pass
    
    @abstractmethod
    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata."""
        pass
    
    @abstractmethod
    async def list_files(self, prefix: Optional[str] = None) -> AsyncIterator[FilePath]:
        """List files."""
        pass
    
    # Hook methods (can be overridden by subclasses)
    async def _pre_write(self, file_path: FilePath, content: bytes) -> None:
        """Hook called before write operation."""
        pass
    
    async def _post_write(self, file_path: FilePath, metadata: FileMetadata) -> None:
        """Hook called after successful write operation."""
        pass
    
    async def _pre_read(self, file_path: FilePath) -> None:
        """Hook called before read operation."""
        pass
    
    async def _post_read(self, file_path: FilePath, content: Optional[bytes]) -> None:
        """Hook called after read operation."""
        pass
    
    async def _pre_delete(self, file_path: FilePath) -> None:
        """Hook called before delete operation."""
        pass
    
    async def _post_delete(self, file_path: FilePath, success: bool) -> None:
        """Hook called after delete operation."""
        pass
    
    async def _handle_write_error(self, file_path: FilePath, error: Exception) -> None:
        """Handle write errors."""
        pass
    
    async def _handle_read_error(self, file_path: FilePath, error: Exception) -> None:
        """Handle read errors."""
        pass
    
    async def _handle_delete_error(self, file_path: FilePath, error: Exception) -> None:
        """Handle delete errors."""
        pass
    
    def _create_metadata(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Create file metadata."""
        return FileMetadata(
            id=uuid4(),
            file_path=file_path,
            size=FileSize(len(content)),
            content_type="application/octet-stream",
            created_at=datetime.utcnow()
        )