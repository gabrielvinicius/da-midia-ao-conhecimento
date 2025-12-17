"""Bootstrap module for storage services (legacy helper)."""
from typing import Any, Dict

from src.storage.application.services.storage_service import StorageService
from src.storage.infrastructure.persistence.local_storage_repository import (
    LocalStorageService,
)


def bootstrap_storage_module(storage_provider: str = "local") -> Dict[str, Any]:
    """Constructs storage services using the configured provider."""
    if storage_provider != "local":
        # For now, fallback to local; extend when real providers available
        storage_provider = "local"

    repository = LocalStorageService(root_directory="storage")
    storage_service = StorageService(repository=repository)

    return {
        "storage_service": storage_service,
        "repository": repository,
    }
