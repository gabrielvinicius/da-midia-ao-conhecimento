"""Domain level interfaces for the storage module."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Protocol

from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class StorageProviderError(Exception):
    """Raised when a storage provider encounters an unrecoverable error."""


class StorageConfiguration(ABC):
    """Base class for provider configuration objects."""

    @abstractmethod
    def get_config(self) -> dict:
        """Return a serialisable representation of the configuration."""

    @abstractmethod
    def validate_config(self) -> bool:
        """Return True when the configuration is valid."""


class StorageProvider(ABC):
    """Contract implemented by all storage providers."""

    def __init__(self, config: StorageConfiguration):
        self._config = config
        if not config.validate_config():
            raise StorageProviderError("Invalid storage configuration provided")

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human readable identifier for the provider."""

    @abstractmethod
    async def upload(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Persist file content and return metadata."""

    @abstractmethod
    async def download(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content if available."""

    @abstractmethod
    async def delete(self, file_path: FilePath) -> bool:
        """Remove file content if it exists."""

    @abstractmethod
    async def exists(self, file_path: FilePath) -> bool:
        """Return True when the file exists in the backing store."""

    @abstractmethod
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Return persisted metadata when available."""


class StorageProviderFactory(Protocol):
    """Factory that resolves provider implementations by name."""

    def __call__(self, provider_name: str) -> StorageProvider:  # pragma: no cover - structural typing
        ...


# Re-export repository abstraction used across the code base.
from src.storage.domain.repositories.storage_repository import StorageRepository  # noqa: E402


__all__ = [
    "StorageConfiguration",
    "StorageProvider",
    "StorageProviderFactory",
    "StorageProviderError",
    "StorageRepository",
    "FileMetadata",
    "FilePath",
    "FileSize",
]
