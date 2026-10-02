"""Factory e helpers para resolver serviços de storage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.storage.infrastructure.adapters.s3_storage_adapter import S3StorageRepository
from src.storage.application.ports import (
    StorageRepositoryPort,
    StorageServiceResolverPort,
    FileStoragePort,
)
from src.storage.application.services.storage_service import StorageService
from src.storage.config.settings import storage_settings
from src.storage.infrastructure.persistence.local_storage_repository import (
    LocalStorageService,
)

logger = structlog.get_logger(__name__)


@dataclass
class StorageClientAdapter(FileStoragePort):
    """Arquivos das mídias para os demais módulos, sempre sem carregá-los
    inteiros na memória: grava a partir de um temporário, lê por trechos e
    baixa direto para o disco."""

    service: StorageService
    provider_name: str

    async def upload_file(self, *, source_path: str, destination: str, content_type: str) -> Dict[str, Any]:
        """Grava o arquivo enviado a partir do temporário da API."""
        file_meta = await self.service.store_file_from(str(Path(destination)), source_path)
        return {
            "path": str(file_meta.file_path),
            "provider": self.provider_name,
            "content_type": file_meta.content_type,
            "size": file_meta.size.bytes,
        }

    async def size(self, path: Any) -> Optional[int]:
        meta = await self.service.get_file_metadata(str(path))
        return meta.size.bytes if meta else None

    async def read_range(self, path: Any, start: int, end: int) -> Optional[bytes]:
        return await self.service.read_file_range(str(path), start, end)

    async def download_to(self, path: Any, destination: str) -> bool:
        """Grava o arquivo em ``destination`` (vídeos de até 500 MB não passam pela memória)."""
        return await self.service.download_file_to(str(path), destination)

    async def delete(self, file_path: str) -> bool:
        return await self.service.delete_file(file_path)

    async def delete_folder(self, folder_path: str) -> bool:
        return await self.service.delete_folder(folder_path)

    async def exists(self, file_path: str) -> bool:
        return await self.service.file_exists(file_path)

    async def list_files(self, prefix: str = "") -> List[str]:
        """Lists all files in the storage system matching the prefix."""
        return await self.service.list_files(prefix)


class StorageServiceFactory(StorageServiceResolverPort):
    """Resolves storage services based on the provider."""

    def __init__(self) -> None:
        self._repositories: Dict[str, StorageRepositoryPort] = {"local": LocalStorageService()}
        # Metadados exibidos na escolha do armazenamento.
        self._meta: Dict[str, Dict[str, Any]] = {
            "local": {
                "label": "Local (Filesystem)",
                "description": "Armazenamento local no filesystem",
                "public": True,
                "capabilities": {"upload": True, "download": True},
            },
        }
        # S3 só é oferecido quando há um bucket configurado; antes, a opção
        # existia sempre e gravava no disco local.
        if storage_settings.s3_configured:
            self._repositories["s3"] = S3StorageRepository(
                bucket=storage_settings.s3_bucket,
                endpoint_url=storage_settings.s3_endpoint_url,
                access_key=storage_settings.s3_access_key,
                secret_key=storage_settings.s3_secret_key,
                region=storage_settings.s3_region,
            )
            self._meta["s3"] = {
                "label": "S3 / MinIO",
                "description": f"Bucket {storage_settings.s3_bucket} em serviço compatível com S3",
                "public": True,
                "capabilities": {"upload": True, "download": True},
            }
        self._allowed = set(storage_settings.providers_allowed or self._repositories) & set(
            self._repositories
        )

    def _get_service(self, provider: str) -> StorageClientAdapter:
        if provider not in self._allowed:
            raise ValueError(
                f"Provider '{provider}' not allowed; allowed={sorted(self._allowed)}"
            )
        try:
            repo = self._repositories[provider]
            service = StorageService(repository=repo)
            return StorageClientAdapter(service, provider)
        except KeyError as exc:
            raise ValueError(f"Provider '{provider}' não suportado") from exc

    def create_storage_service(self, provider: str) -> FileStoragePort:
        """Returns an adapter compatible with current media module callers."""
        return self._get_service(provider)

    def get_download_service(self, provider: str) -> FileStoragePort:
        """Resolves a download service."""
        return self.create_storage_service(provider)

    def get_provider_root(self, provider: str) -> Path:
        """Returns the root directory of the configured provider (when applicable)."""
        try:
            repo = self._repositories[provider]
            root = getattr(repo, "_root", None)
            if root is None:
                raise ValueError(f"Provider '{provider}' não expõe caminho local")
            return root
        except KeyError as exc:
            raise ValueError(f"Provider '{provider}' não suportado") from exc

    def list_allowed_providers(self) -> List[str]:
        """Lista providers permitidos e efetivamente registrados."""
        available = set(self._repositories.keys())
        allowed = sorted(self._allowed.intersection(available))
        return allowed

    def provider_meta(self, name: str) -> Dict[str, Any]:
        base = self._meta.get(name, {})
        return {
            "label": base.get("label", name),
            "description": base.get("description", ""),
            "public": base.get("public", True),
            "capabilities": base.get("capabilities", {}),
        }


def get_storage_service_factory() -> StorageServiceFactory:
    return StorageServiceFactory()


__all__ = ["StorageServiceFactory", "get_storage_service_factory"]
