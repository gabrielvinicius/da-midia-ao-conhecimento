"""Factory and helpers to resolve storage services."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.storage.application.services.storage_service import StorageService
from src.storage.infrastructure.local_storage_service import LocalStorageService
from src.storage.domain.repositories.storage_repository import StorageRepository

logger = structlog.get_logger(__name__)


@dataclass
class StorageClientAdapter:
    """Adapter exposing a uniform interface for upload/download used by other modules.
    Wraps the Application Service to maintain backward compatibility.
    """

    service: StorageService
    provider_name: str

    async def upload(
        self,
        *,
        destination_path: str,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Ensure deterministic, non-legacy path layout
        normalized_path = str(Path(destination_path))
        
        # Use new Service API
        file_meta = await self.service.store_file(normalized_path, content)
        
        return {
            "path": str(file_meta.file_path),
            "provider": self.provider_name,
            "content_type": file_meta.content_type,
            "metadata": metadata or {},
            "size": file_meta.size.bytes
        }

    async def download(self, file_path: str):
        # Legacy expects tuple (bytes, filename) or similar?
        # Old LocalStorageService returned (bytes, filename).
        # S3Stub returned (bytes, filename).
        # New Service returns bytes or None.
        
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
                f"File '{normalized_path}' not found in storage provider '{self.provider_name}'"
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
                f"File '{normalized_path}' not found in storage provider '{self.provider_name}'"
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


class StorageServiceFactory:
    """Resolves storage services based on the provider."""

    def __init__(self) -> None:
        # Initialize repositories
        self._repositories: Dict[str, StorageRepository] = {
            "local": LocalStorageService(),
            "s3": S3StorageService(),
        }

    def _get_service(self, provider: str) -> StorageClientAdapter:
        try:
            repo = self._repositories[provider]
            service = StorageService(repository=repo)
            return StorageClientAdapter(service, provider)
        except KeyError as exc:
            raise ValueError(f"Provider '{provider}' not supported") from exc

    def create_storage_service(self, provider: str) -> Any:
        """Returns an adapter compatible with current media module callers."""
        return self._get_service(provider)

    def get_download_service(self, provider: str) -> Any:
        """Resolves a download service."""
        return self.create_storage_service(provider)

    def get_provider_root(self, provider: str) -> Path:
        """Returns the root directory of the configured provider (when applicable)."""
        try:
            repo = self._repositories[provider]
            # Assuming implementations expose _root or we can access it.
            # Both Local and S3 (stub) expose _root.
            root = getattr(repo, "_root", None)
            if root is None:
                raise ValueError(f"Provider '{provider}' does not expose local path")
            return root
        except KeyError as exc:
            raise ValueError(f"Provider '{provider}' not supported") from exc


def get_storage_service_factory() -> StorageServiceFactory:
    return StorageServiceFactory()


__all__ = ["StorageServiceFactory", "get_storage_service_factory"]
