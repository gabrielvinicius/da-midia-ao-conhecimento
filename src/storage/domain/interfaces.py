# src/storage/domain/interfaces.py
"""
Domain interfaces for storage module following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator, Dict, Any
from datetime import datetime

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath


class StorageReader(ABC):
    """Interface for read operations - ISP compliance."""
    
    @abstractmethod
    async def read(self, file_path: FilePath) -> Optional[bytes]:
        """Read file content."""
        pass
    
    @abstractmethod
    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata."""
        pass


class StorageWriter(ABC):
    """Interface for write operations - ISP compliance."""
    
    @abstractmethod
    async def write(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Write file content."""
        pass
    
    @abstractmethod
    async def delete(self, file_path: FilePath) -> bool:
        """Delete file."""
        pass


class StorageProvider(StorageReader, StorageWriter):
    """Complete storage interface combining read/write operations."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass
    
    @abstractmethod
    async def list_files(self, prefix: Optional[str] = None) -> AsyncIterator[FilePath]:
        """List files with optional prefix filter."""
        pass


class StorageConfiguration(ABC):
    """Interface for storage configuration - SRP compliance."""
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate configuration."""
        pass


class StorageHealthCheck(ABC):
    """Interface for health checks - SRP compliance."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check storage provider health."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


class StorageOperationLogger(ABC):
    """Interface for operation logging - SRP compliance."""
    
    @abstractmethod
    async def log_operation(
        self, 
        operation: str, 
        file_path: FilePath, 
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """Log storage operation."""
        pass


class StorageMetrics(ABC):
    """Interface for metrics collection - SRP compliance."""
    
    @abstractmethod
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool
    ) -> None:
        """Record operation metrics."""
        pass


class StorageProviderFactory(ABC):
    """Factory interface for creating storage providers - DIP compliance."""
    
    @abstractmethod
    def create_provider(self, provider_type: str, config: StorageConfiguration) -> StorageProvider:
        """Create storage provider instance."""
        pass
    
    @abstractmethod
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        pass


class StorageRepository(ABC):
    """High-level repository interface - DIP compliance."""
    
    @abstractmethod
    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file with business logic."""
        pass
    
    @abstractmethod
    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content."""
        pass
    
    @abstractmethod
    async def remove(self, file_path: FilePath) -> bool:
        """Remove file."""
        pass
    
    @abstractmethod
    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata."""
        pass