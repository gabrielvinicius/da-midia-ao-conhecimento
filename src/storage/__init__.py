# src/storage/__init__.py
"""Lightweight storage package exposing the utilities required by tests."""

from src.storage.application.storage_service import StorageException, StorageService
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.interfaces import (
    StorageConfiguration,
    StorageProvider,
    StorageProviderError,
    StorageProviderFactory,
    StorageRepository,
)
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize
from src.storage.infrastructure.local_storage_service import LocalStorageService

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
