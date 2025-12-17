# src/storage/__init__.py
"""Lightweight storage package exposing the utilities required by tests."""

from src.storage.application.ports import (
    StorageConfigurationPort as StorageConfiguration,
)
from src.storage.application.ports import (
    StorageProviderError,
)
from src.storage.application.ports import (
    StorageProviderFactoryPort as StorageProviderFactory,
)
from src.storage.application.ports import (
    StorageProviderPort as StorageProvider,
)
from src.storage.application.ports import (
    StorageRepositoryPort as StorageRepository,
)
from src.storage.application.services.storage_service import StorageService
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize
from src.storage.infrastructure.persistence.local_storage_repository import (
    LocalStorageService,
)

# Alias for backward compatibility if needed, or just remove if tests adapt
StorageException = StorageProviderError

__all__ = [
    "StorageService",
    "StorageException",
    "FileMetadata",
    "FilePath",
    "FileSize",
    "StorageConfiguration",
    "StorageProvider",
    "StorageProviderFactory",
    "StorageProviderError",
    "StorageRepository",
    "LocalStorageService",
]
