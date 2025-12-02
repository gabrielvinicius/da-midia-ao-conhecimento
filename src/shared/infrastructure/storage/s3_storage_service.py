"""S3StorageService (stub):
Implementação mínima para atender dependências atuais sem acessar S3.
Faz fallback para o filesystem local, útil em desenvolvimento/testes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.storage.application.storage_service import StorageException, StorageService
from src.shared.resilience.policies import create_retry_policy
from src.providers.domain.interfaces import ProviderCapability, ProviderType


class S3StorageService(StorageService):
    """Adaptador simples que utiliza o filesystem local simulando S3."""

    def __init__(self, root_directory: Union[str, Path] = "storage") -> None:
        self._root = Path(root_directory)
        self._root.mkdir(parents=True, exist_ok=True)
        self._config = {"root_directory": str(root_directory)}

    @property
    def provider_name(self) -> str:
        return "s3"

    # --- IProvider Implementation ---

    def get_name(self) -> str:
        return "s3-stub"

    def get_type(self) -> ProviderType:
        return ProviderType.STORAGE

    def get_version(self) -> str:
        return "0.1.0"

    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.READ,
            ProviderCapability.WRITE,
            ProviderCapability.DELETE,
            ProviderCapability.LIST
        ]

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "root": str(self._root), "exists": self._root.exists()}

    def get_configuration(self) -> Dict[str, Any]:
        return self._config

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if "root_directory" in config:
            self._root = Path(config["root_directory"])
            self._root.mkdir(parents=True, exist_ok=True)
            self._config = config
        return True

    async def cleanup(self) -> None:
        pass

    # --- StorageService Implementation ---

    @create_retry_policy(exceptions=(StorageException, OSError))
    async def upload(self, file_path: Union[str, Path], file: bytes) -> bool:
        destination = self._resolve_path(file_path)
        try:
            await asyncio.to_thread(self._write, destination, file)
        except Exception as exc:  # pragma: no cover - defensive branch
            raise StorageException("Failed to store file on S3 stub", exc) from exc
        return True

    @create_retry_policy(exceptions=(StorageException, OSError))
    async def download(self, file_path: Union[str, Path]) -> Optional[Tuple[bytes, str]]:
        source = self._resolve_path(file_path)
        if not source.exists():
            return None
        try:
            data = await asyncio.to_thread(source.read_bytes)
            return data, source.name
        except Exception as exc:  # pragma: no cover - defensive branch
            raise StorageException("Failed to download file from S3 stub", exc) from exc

    @create_retry_policy(exceptions=(StorageException, OSError))
    async def delete(self, file_path: Union[str, Path]) -> bool:
        target = self._resolve_path(file_path)
        if not target.exists():
            return False
        try:
            await asyncio.to_thread(target.unlink)
            return True
        except Exception as exc:  # pragma: no cover - defensive branch
            raise StorageException("Failed to delete file from S3 stub", exc) from exc

    async def exists(self, file_path: Union[str, Path]) -> bool:
        return self._resolve_path(file_path).exists()

    async def download_file(self, file_path: Union[str, Path]) -> bytes:
        """Compat helper para consumidores que esperam apenas os bytes."""
        result = await self.download(file_path)
        if result is None:
            raise FileNotFoundError(f"File '{file_path}' not found in S3 stub")
        payload, _ = result
        return payload

    def _resolve_path(self, file_path: Union[str, Path]) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self._root / path

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


__all__ = ["S3StorageService"]
