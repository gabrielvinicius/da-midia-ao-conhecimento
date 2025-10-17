# src/storage/domain/services/storage_coordinator.py
"""
Domain service for coordinating storage operations - SRP compliance.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.interfaces import (
    StorageProvider, 
    StorageOperationLogger, 
    StorageMetrics
)
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class StorageOperationError(Exception):
    """Domain exception for storage operation errors."""
    pass


class StorageCoordinator:
    """
    Domain service that coordinates storage operations with logging and metrics.
    Follows SRP by focusing only on coordination logic.
    """
    
    def __init__(
        self,
        provider: StorageProvider,
        logger: StorageOperationLogger,
        metrics: StorageMetrics
    ):
        self._provider = provider
        self._logger = logger
        self._metrics = metrics
    
    async def store_file(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file with logging and metrics."""
        start_time = datetime.utcnow()
        success = False
        error = None
        
        try:
            # Create metadata
            metadata = FileMetadata(
                id=uuid4(),
                file_path=file_path,
                size=FileSize(len(content)),
                content_type="application/octet-stream",  # Should be injected
                created_at=start_time
            )
            
            # Store through provider
            result = await self._provider.write(file_path, content)
            success = True
            return result
            
        except Exception as e:
            error = e
            success = False
            raise StorageOperationError(f"Failed to store file {file_path}: {e}") from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation="store",
                file_path=file_path,
                success=success,
                duration=duration,
                error=error
            )
            
            # Record metrics
            await self._metrics.record_operation(
                operation="store",
                provider=self._provider.provider_name,
                duration=duration,
                success=success
            )
    
    async def retrieve_file(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file with logging and metrics."""
        start_time = datetime.utcnow()
        success = False
        error = None
        
        try:
            content = await self._provider.read(file_path)
            success = content is not None
            return content
            
        except Exception as e:
            error = e
            success = False
            raise StorageOperationError(f"Failed to retrieve file {file_path}: {e}") from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            await self._logger.log_operation(
                operation="retrieve",
                file_path=file_path,
                success=success,
                duration=duration,
                error=error
            )
            
            await self._metrics.record_operation(
                operation="retrieve",
                provider=self._provider.provider_name,
                duration=duration,
                success=success
            )
    
    async def delete_file(self, file_path: FilePath) -> bool:
        """Delete file with logging and metrics."""
        start_time = datetime.utcnow()
        success = False
        error = None
        
        try:
            result = await self._provider.delete(file_path)
            success = result
            return result
            
        except Exception as e:
            error = e
            success = False
            raise StorageOperationError(f"Failed to delete file {file_path}: {e}") from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            await self._logger.log_operation(
                operation="delete",
                file_path=file_path,
                success=success,
                duration=duration,
                error=error
            )
            
            await self._metrics.record_operation(
                operation="delete",
                provider=self._provider.provider_name,
                duration=duration,
                success=success
            )