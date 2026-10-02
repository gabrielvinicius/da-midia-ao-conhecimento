"""Remoção de arquivos usada na exclusão de mídias."""
from __future__ import annotations

from typing import Protocol

import structlog

logger = structlog.get_logger(__name__)


class StorageMaintenancePort(Protocol):
    """Port exposing minimal storage operations required for maintenance."""

    async def delete(self, provider_name: str, path: str) -> None: ...

    async def delete_folder(self, provider_name: str, folder_path: str) -> None: ...


class StorageMaintenanceService:
    """Apaga os arquivos de uma mídia excluída.

    Não há varredura de órfãos: o envio apaga o arquivo se a mídia não for
    gravada, e a exclusão não apaga nada do banco se o arquivo não sair.
    """

    def __init__(self, storage_port: StorageMaintenancePort) -> None:
        self._storage = storage_port

    async def delete_file(self, provider_name: str, path: str) -> None:
        """Delete a single file, used by higher-level services (e.g., media delete)."""
        await self._storage.delete(provider_name, path)

    async def delete_folder(self, provider_name: str, folder_path: str) -> None:
        """Delete an entire folder/prefix, useful for deep media cleanup."""
        await self._storage.delete_folder(provider_name, folder_path)
