from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from src.shared.application.observability import LoggerPort, MetricsPort
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath


class StorageMetricsPort(MetricsPort, Protocol):
    """Metrics for storage operations."""

    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool,
    ) -> None: ...


class StorageOperationLoggerPort(LoggerPort, Protocol):
    """Logger for storage operations."""

    async def log_operation(
        self,
        operation: str,
        file_path: FilePath,
        success: bool,
        duration: float,
        error: Optional[Exception] = None,
        **extra: Any,
    ) -> None: ...


class StorageRepositoryPort(Protocol):
    """Port for storage repositories used by the application service."""

    @property
    def provider_name(self) -> str: ...

    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata: ...

    async def retrieve(self, file_path: FilePath) -> Optional[bytes]: ...

    async def download_to(self, file_path: FilePath, destination: str) -> bool:
        """Grava o arquivo em ``destination`` sem carregá-lo inteiro na memória.
        False se o arquivo não existir."""
        ...

    async def remove(self, file_path: FilePath) -> bool: ...

    async def remove_folder(self, folder_path: str) -> bool: ...

    async def exists(self, file_path: FilePath) -> bool: ...

    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]: ...

    async def list_files(self, prefix: str = "") -> List[str]: ...


class FileStoragePort(Protocol):
    """Narrow upload/download port used by media_management."""

    async def upload(
        self,
        *,
        file_data: bytes,
        destination: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    async def download_file(self, file_path: str) -> bytes: ...


class StorageServiceResolverPort(Protocol):
    """Port for resolving storage services by provider name."""

    def create_storage_service(self, provider: str) -> FileStoragePort: ...
    
    def get_download_service(self, provider: str) -> FileStoragePort: ...


class FileReferenceValidatorPort(Protocol):
    """Protocol for modules that hold references to files in storage."""

    async def validate_batch(self, provider: str, paths: List[str]) -> Any:
        """Given a list of file paths, return the set of paths that are valid/referenced."""
        ...


__all__ = [
    "StorageMetricsPort",
    "StorageOperationLoggerPort",
    "StorageRepositoryPort",
    "FileStoragePort",
    "StorageServiceResolverPort",
    "FileReferenceValidatorPort",
]