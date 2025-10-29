"""
Factory e helpers para resolver serviços de storage usados em uploads.

Fornece uma API simples compatível com os chamadores atuais.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.storage.infrastructure.local_storage_service import LocalStorageService


@dataclass
class _UploadAdapter:
    """Adapter que expõe uma interface uniforme para upload usada no módulo de mídia."""

    backend: LocalStorageService

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
        }

    async def delete(self, file_path: str) -> bool:  # compat extra
        return await self.backend.delete(file_path)


class StorageServiceFactory:
    """Resolve serviços de storage com base no provider informado."""

    def __init__(self) -> None:
        self._local = LocalStorageService()

    def create_storage_service(self, provider: str) -> Any:
        # No momento, só há adapter local; pode ser estendido para S3/Azure etc
        return _UploadAdapter(self._local)


def get_storage_service_factory() -> StorageServiceFactory:
    return StorageServiceFactory()


__all__ = ["StorageServiceFactory", "get_storage_service_factory"]
