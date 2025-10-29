"""
S3StorageService (stub):
Implementação mínima para atender dependências atuais sem acessar S3.
Faz fallback para o filesystem local, útil em desenvolvimento/testes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path


class S3StorageService:
    """Adaptador simples que lê/grava no filesystem local.

    Em produção, substitua por uma implementação real que use boto3/minio.
    """

    def __init__(self, root_directory: str = "storage") -> None:
        self._root = Path(root_directory)
        self._root.mkdir(parents=True, exist_ok=True)

    async def download_file(self, file_path: str) -> bytes:
        """Lê um arquivo do disco, simulando download do S3."""
        path = self._resolve_path(file_path)
        return await asyncio.to_thread(path.read_bytes)

    async def upload_file(self, file_path: str, content: bytes) -> bool:
        """Grava um arquivo no disco, simulando upload para o S3."""
        path = self._resolve_path(file_path)
        await asyncio.to_thread(self._write, path, content)
        return True

    def _resolve_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self._root / path

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


__all__ = ["S3StorageService"]
