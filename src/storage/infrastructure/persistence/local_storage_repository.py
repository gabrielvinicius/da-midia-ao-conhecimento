"""Simple local filesystem storage implementation used in tests."""
from __future__ import annotations

import asyncio
import errno
import os
import shutil
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union
from uuid import uuid4

from src.storage.application.ports import StorageRepositoryPort
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class LocalStorageService(StorageRepositoryPort):
    """Persist files on the local filesystem using asynchronous wrappers."""

    def __init__(self, root_directory: Union[str, Path] = "storage") -> None:
        self._root = Path(root_directory)
        self._root.mkdir(parents=True, exist_ok=True)
        self._config = {"root_directory": str(root_directory)}

    @property
    def provider_name(self) -> str:
        return "local"

    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        """Store file and return metadata."""
        destination = self._resolve_path(file_path)

        try:
            await asyncio.to_thread(self._write_file, destination, content)

            # Create metadata
            stat = destination.stat()
            size = FileSize(stat.st_size)
            mime_type, _ = mimetypes.guess_type(destination)

            return FileMetadata(
                id=uuid4(),
                file_path=file_path,
                size=size,
                content_type=mime_type or "application/octet-stream",
                created_at=datetime.fromtimestamp(stat.st_ctime, timezone.utc),
                updated_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            )
        except Exception as exc:
            raise Exception(
                f"Falha ao gravar arquivo {file_path}: {exc}"
            ) from exc

    async def store_from(self, file_path: FilePath, source_path: str, *, move: bool = False) -> FileMetadata:
        destination = self._resolve_path(file_path)

        def _store() -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if move:
                try:
                    # Mesmo disco: só troca o nome. Copiar os 433 MB de uma
                    # entrevista levava 2,5 s na conclusão do envio.
                    os.replace(source_path, destination)
                    return
                except OSError as exc:
                    if exc.errno != errno.EXDEV:
                        raise
            shutil.copyfile(source_path, destination)
            if move:
                os.remove(source_path)

        await asyncio.to_thread(_store)
        return await self.get_metadata(file_path)

    async def read_range(self, file_path: FilePath, start: int, end: int) -> Optional[bytes]:
        source = self._resolve_path(file_path)
        if not source.exists():
            return None

        def _read() -> bytes:
            with open(source, "rb") as handle:
                handle.seek(start)
                return handle.read(end - start + 1)

        return await asyncio.to_thread(_read)

    async def download_to(self, file_path: FilePath, destination: str) -> bool:
        source = self._resolve_path(file_path)
        if not source.exists():
            return False
        await asyncio.to_thread(shutil.copyfile, source, destination)
        return True

    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        """Retrieve file content."""
        source = self._resolve_path(file_path)
        if not source.exists():
            return None
        try:
            return await asyncio.to_thread(source.read_bytes)
        except Exception as exc:
            raise Exception(
                f"Falha ao ler arquivo {file_path}: {exc}"
            ) from exc

    async def remove(self, file_path: FilePath) -> bool:
        """Remove file. Returns True if removed, False if not found."""
        target = self._resolve_path(file_path)
        if not target.exists():
            return False
        try:
            await asyncio.to_thread(target.unlink)
            return True
        except Exception as exc:
            raise Exception(
                f"Falha ao remover arquivo {file_path}: {exc}"
            ) from exc

    async def remove_folder(self, folder_path: str) -> bool:
        """Remove a pasta e tudo o que há nela. False se ela não existir.

        Recusa caminhos fora da raiz do armazenamento (ex.: "../").
        """
        root = self._root.resolve()
        target = (root / folder_path).resolve()
        if target == root or root not in target.parents:
            raise ValueError(f"Pasta fora do armazenamento: {folder_path}")
        if not target.is_dir():
            return False
        await asyncio.to_thread(shutil.rmtree, target)
        return True

    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists."""
        return self._resolve_path(file_path).exists()

    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata without content."""
        target = self._resolve_path(file_path)
        if not target.exists():
            return None

        try:
            stat = await asyncio.to_thread(target.stat)
            size = FileSize(stat.st_size)
            mime_type, _ = mimetypes.guess_type(target)

            return FileMetadata(
                id=uuid4(), # Local files don't have persistent IDs, generate one
                file_path=file_path,
                size=size,
                content_type=mime_type or "application/octet-stream",
                created_at=datetime.fromtimestamp(stat.st_ctime, timezone.utc),
                updated_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            )
        except Exception as exc:
             raise Exception(
                 f"Falha ao obter metadados de {file_path}: {exc}"
             ) from exc

    async def list_files(self, prefix: str = "") -> List[str]:
        """Lists files in the local storage."""
        base_dir = self._root
        if prefix:
            base_dir = base_dir / prefix

        if not base_dir.exists():
            return []

        def _gather() -> List[str]:
            files = []
            for path in base_dir.rglob("*"):
                if path.is_file():
                    rel_path = path.relative_to(self._root).as_posix()
                    files.append(rel_path)
            return files

        try:
            return await asyncio.to_thread(_gather)
        except Exception as exc:
            raise Exception(f"Falha ao listar arquivos: {exc}") from exc

    def _resolve_path(self, file_path: FilePath) -> Path:
        # FilePath já garante um caminho relativo, sem "..".
        return self._root / file_path.to_path()

    @staticmethod
    def _write_file(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


__all__ = ["LocalStorageService"]

