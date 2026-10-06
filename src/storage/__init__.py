"""Pacote `storage`.

Mantém exports estáveis (ports, VOs e services) sem acoplar o módulo a bootstraps.
"""

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

__all__ = [
    "StorageService",
    "FileMetadata",
    "FilePath",
    "FileSize",
    "StorageRepository",
    "LocalStorageService",
]
