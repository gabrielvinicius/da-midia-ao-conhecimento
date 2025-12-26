from __future__ import annotations

from src.media_management.application.ports import StorageDownloaderPort
from src.storage.infrastructure.dependencies.providers import StorageServiceFactory


class StorageDownloaderAdapter(StorageDownloaderPort):
    """Adapter for downloading files from storage."""

    def __init__(self, factory: StorageServiceFactory) -> None:
        self._factory = factory

    async def download(self, provider_name: str, path: str) -> bytes:
        storage = self._factory.get_download_service(provider_name)
        return await storage.download_file(path)
