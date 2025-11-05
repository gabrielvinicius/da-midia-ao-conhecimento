"""Factory e helpers para resolver serviços de storage usados em uploads e downloads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.storage.application.storage_service import StorageService
from src.storage.infrastructure.local_storage_service import LocalStorageService


@dataclass
class StorageClientAdapter:
    """Adapter que expõe uma interface uniforme para upload/download usada pelos módulos."""

    backend: StorageService

    async def upload(
        self,
        *,
        destination_path: str,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        await self.backend.upload(destination_path, content)
        return {
            "path": destination_path,
            "provider": self.backend.provider_name,
            "content_type": content_type or "application/octet-stream",
            "metadata": metadata or {},
        }

    async def download(self, file_path: str):
        return await self.backend.download(file_path)

    async def download_file(self, file_path: str) -> bytes:
        result = await self.backend.download(file_path)
        if result is None:
            raise FileNotFoundError(
                f"File '{file_path}' not found in storage provider '{self.backend.provider_name}'"
            )
        payload, _ = result
        return payload

    async def delete(self, file_path: str) -> bool:
        return await self.backend.delete(file_path)

    async def exists(self, file_path: str) -> bool:
        return await self.backend.exists(file_path)


class StorageServiceFactory:
    """Resolve serviços de storage com base no provider informado."""

    def __init__(self) -> None:
        self._providers: Dict[str, StorageService] = {
            "local": LocalStorageService(),
            "s3": S3StorageService(),
        }

    def _get_service(self, provider: str) -> StorageService:
        try:
            return self._providers[provider]
        except KeyError as exc:
            raise ValueError(f"Provider '{provider}' não suportado") from exc

    def create_storage_service(self, provider: str) -> Any:
        """Retorna um adapter compatível com os chamadores atuais do módulo de mídia."""
        service = self._get_service(provider)
        return StorageClientAdapter(service)

    def get_download_service(self, provider: str) -> Any:
        """Resolve um serviço de download compatível com o provider informado."""
        return self.create_storage_service(provider)

    def get_provider_root(self, provider: str) -> Path:
        """Retorna o diretório raiz do provider configurado (quando aplicável)."""
        service = self._get_service(provider)
        root = getattr(service, "_root", None)
        if root is None:
            raise ValueError(f"Provider '{provider}' não expõe caminho local")
        return root


def get_storage_service_factory() -> StorageServiceFactory:
    return StorageServiceFactory()


__all__ = ["StorageServiceFactory", "get_storage_service_factory"]
