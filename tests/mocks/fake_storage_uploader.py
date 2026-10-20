"""Uploader de armazenamento em memória usado em modo lightweight de testes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from src.media_management.application.ports import UploadResult
from tests.mocks.in_memory_storage import InMemoryStorage


@dataclass
class FakeStorageUploadAdapter:
    storage: InMemoryStorage

    async def upload_file(self, *, source_path: str, destination: str, content_type: str, move: bool = False) -> Dict:
        # Lê o temporário da API e guarda em memória
        content = Path(source_path).read_bytes()
        await self.storage.store(file_path=destination, content=content)
        if move:
            Path(source_path).unlink()
        return {"path": destination, "size": len(content), "content_type": content_type}


class FakeStorageUploader:
    def __init__(self, adapter: FakeStorageUploadAdapter):
        self.adapter = adapter

    async def upload(self, command, media_id, content_type: str) -> UploadResult:
        metadata = await self.adapter.upload_file(
            source_path=command.file_path,
            destination=f"{command.user_id}/{media_id}/{command.filename}",
            content_type=content_type,
            move=command.move_source,
        )
        return UploadResult(destination_path=metadata["path"], metadata=metadata)

    async def discard(self, command, destination_path: str) -> None:
        if command.move_source:
            Path(command.file_path).write_bytes(await self.adapter.storage.retrieve(destination_path))
        await self.adapter.storage.remove(destination_path)


__all__ = ["FakeStorageUploader", "FakeStorageUploadAdapter"]
