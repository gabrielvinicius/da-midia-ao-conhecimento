"""Factory e helpers para resolver serviços de storage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from src.storage.infrastructure.adapters.s3_stub_adapter import S3StorageService
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
    """Adapter exposing a uniform interface for upload/download used by other modules.
    Wraps the Application Service to maintain backward compatibility.
    """

    service: StorageService
    provider_name: str

    async def upload(
        self,
        *,
        file_data: bytes,
        destination: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Ensure deterministic path layout
        normalized_path = str(Path(destination))

        # Use new Service API
        file_meta = await self.service.store_file(normalized_path, file_data)

        return {
            "path": str(file_meta.file_path),
            "provider": self.provider_name,
            "content_type": file_meta.content_type,
            "metadata": metadata or {},
            "size": file_meta.size.bytes
        }

    async def retrieve(self, path: Any):
        """Compat: usado por services que esperam StoragePort.retrieve(FilePath)."""
        normalized_path = str(path)
        return await self.service.retrieve_file(normalized_path)

    async def download(self, file_path: str):
        normalized_path = str(Path(file_path))
        data = await self.service.retrieve_file(normalized_path)
        if data is None:
            return None

        # Reconstruct filename from path
        filename = Path(normalized_path).name
        return data, filename

    async def download_file(self, file_path: str) -> bytes:
        normalized_path = str(Path(file_path))
        data = await self.service.retrieve_file(normalized_path)
        if data is None:
            raise FileNotFoundError(
                (
                    f"File '{normalized_path}' not found in storage provider "
                    f"'{self.provider_name}'"
                )
            )
        return data

    def download_file_sync(self, file_path: str) -> bytes:
        """Synchronous version of download_file for use in Celery tasks."""
        import asyncio
        import concurrent.futures

        def run_async_download():
            async def async_download():
                normalized_path = str(Path(file_path))
                return await self.service.retrieve_file(normalized_path)

            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_download())
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_download)
            result = future.result()

        if result is None:
            normalized_path = str(Path(file_path))
            raise FileNotFoundError(
                (
                    f"File '{normalized_path}' not found in storage provider "
                    f"'{self.provider_name}'"
                )
            )
        return result

    async def delete(self, file_path: str) -> bool:
        return await self.service.delete_file(file_path)

    def delete_sync(self, file_path: str) -> bool:
        """Synchronous version of delete."""
        import asyncio
        import concurrent.futures

        def run_async():
            return asyncio.run(self.service.delete_file(file_path))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            return future.result()

    async def exists(self, file_path: str) -> bool:
        return await self.service.file_exists(file_path)

    def exists_sync(self, file_path: str) -> bool:
        """Synchronous version of exists."""
        import asyncio
        import concurrent.futures

        def run_async():
            return asyncio.run(self.service.file_exists(file_path))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            return future.result()

    async def list_files(self, prefix: str = "") -> List[str]:
        """Lists all files in the storage system matching the prefix."""
        return await self.service.list_files(prefix)


class StorageServiceFactory(StorageServiceResolverPort):
    """Resolves storage services based on the provider."""

    def __init__(self) -> None:
        # Initialize repositories
        self._repositories: Dict[str, StorageRepositoryPort] = {
            "local": LocalStorageService(),
            "s3": S3StorageService(),
        }
        # metadados (label/description/public/capabilities)
        self._meta: Dict[str, Dict[str, Any]] = {
            "local": {
                "label": "Local (Filesystem)",
                "description": "Armazenamento local no filesystem",
                "public": True,
                "capabilities": {"upload": True, "download": True},
            },
            "s3": {
                "label": "S3 / MinIO",
                "description": "Compatível com S3/MinIO (stub filesystem para dev)",
                "public": True,
                "capabilities": {"upload": True, "download": True},
            },
        }
        self._allowed = set(
            storage_settings.providers_allowed or self._repositories.keys()
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