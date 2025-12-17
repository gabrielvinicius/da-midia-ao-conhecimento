from __future__ import annotations

from src.media_processing.application.ports import (
    StorageDownloadServicePort,
    StorageServiceFactoryPort,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory


class StorageDownloadAdapter(StorageServiceFactoryPort):
    """Exposes StorageServiceFactory as a download-capable port."""

    def __init__(self, factory: StorageServiceFactory) -> None:
        self._factory = factory

    def get_download_service(self, provider: str) -> StorageDownloadServicePort:
        return self._factory.create_storage_service(provider)


__all__ = ["StorageDownloadAdapter"]
