from __future__ import annotations

from typing import Optional

from src.media_management.application.ports import StorageDownloaderPort
from src.storage.application.ports import StorageServiceResolverPort


class StorageDownloaderAdapter(StorageDownloaderPort):
    """Lê o arquivo da mídia por trechos no armazenamento escolhido."""

    def __init__(self, factory: StorageServiceResolverPort) -> None:
        self._factory = factory

    async def size(self, provider_name: str, path: str) -> Optional[int]:
        return await self._factory.get_download_service(provider_name).size(path)

    async def read_range(self, provider_name: str, path: str, start: int, end: int) -> Optional[bytes]:
        return await self._factory.get_download_service(provider_name).read_range(path, start, end)
