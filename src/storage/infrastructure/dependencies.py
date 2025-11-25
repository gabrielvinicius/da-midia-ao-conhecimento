"""Factory e helpers para resolver serviços de storage usados em uploads e downloads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.storage.application.storage_service import StorageService
from src.storage.infrastructure.local_storage_service import LocalStorageService


logger = structlog.get_logger(__name__)


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
        result = await self.backend.download(file_path)
        if result is None:
            legacy = self._legacy_lookup(file_path)
            if legacy is not None:
                return legacy, Path(file_path).name
        return result

    async def download_file(self, file_path: str) -> bytes:
        result = await self.backend.download(file_path)
        if result is None:
            legacy_bytes = self._legacy_lookup(file_path)
            if legacy_bytes is None:
                raise FileNotFoundError(
                    f"File '{file_path}' not found in storage provider '{self.backend.provider_name}'"
                )
            return legacy_bytes
        payload, _ = result
        return payload

    def download_file_sync(self, file_path: str) -> bytes:
        """Synchronous version of download_file for use in Celery tasks."""
        # Check if the backend has a synchronous method available
        if hasattr(self.backend, 'download_sync'):
            result = self.backend.download_sync(file_path)
        else:
            # Fallback to running the async method in a new event loop in a separate thread
            import asyncio
            import concurrent.futures
            
            def run_async_download():
                async def async_download():
                    return await self.backend.download(file_path)
                
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
            legacy_bytes = self._legacy_lookup(file_path)
            if legacy_bytes is None:
                raise FileNotFoundError(
                    f"File '{file_path}' not found in storage provider '{self.backend.provider_name}'"
                )
            return legacy_bytes
        if isinstance(result, tuple):
            payload, _ = result
        else:
            payload = result
        return payload

    def _legacy_lookup(self, file_path: str) -> Optional[bytes]:
        """Fallback para registros legados que armazenavam apenas o nome do arquivo."""
        candidate = Path(file_path)
        if candidate.is_absolute() or candidate.parent != Path("."):
            return None
        backend_root = Path(getattr(self.backend, "_root", ""))
        if not backend_root.exists():
            return None
        matches = list(backend_root.rglob(candidate.name))
        if not matches:
            return None
        match = matches[0]
        try:
            logger.warning(
                "storage.legacy_lookup_hit",
                original=file_path,
                resolved=str(match),
                provider=self.backend.provider_name,
            )
            return match.read_bytes()
        except Exception as exc:  # pragma: no cover - filesystem failures
            logger.error(
                "storage.legacy_lookup_failed",
                original=file_path,
                resolved=str(match),
                error=str(exc),
            )
            return None

    async def delete(self, file_path: str) -> bool:
        return await self.backend.delete(file_path)

    def delete_sync(self, file_path: str) -> bool:
        """Synchronous version of delete for use in Celery tasks."""
        if hasattr(self.backend, 'delete_sync'):
            return self.backend.delete_sync(file_path)
        else:
            import asyncio
            import concurrent.futures
            
            def run_async():
                return asyncio.run(self.backend.delete(file_path))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                return future.result()

    async def exists(self, file_path: str) -> bool:
        return await self.backend.exists(file_path)

    def exists_sync(self, file_path: str) -> bool:
        """Synchronous version of exists for use in Celery tasks."""
        if hasattr(self.backend, 'exists_sync'):
            return self.backend.exists_sync(file_path)
        else:
            import asyncio
            import concurrent.futures
            
            def run_async():
                return asyncio.run(self.backend.exists(file_path))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                return future.result()


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
