"""Uploader de armazenamento em memória usado em modo lightweight de testes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from src.media_management.application.ports import UploadResult
from tests.mocks.in_memory_storage import InMemoryStorage


@dataclass
class FakeStorageUploadAdapter:
    storage: InMemoryStorage

    async def upload(self, *, file_data: bytes, destination: str, content_type: str) -> Dict:
        # Armazena bytes em memória e retorna metadados simples
        await self.storage.store(file_path=destination, content=file_data)
        return {"path": destination, "size": len(file_data), "content_type": content_type}


class FakeStorageUploader:
    def __init__(self, adapter: FakeStorageUploadAdapter):
        self.adapter = adapter

    async def upload(self, command, media_id, content_type: str) -> UploadResult:
        metadata = await self.adapter.upload(
            file_data=command.file,
            destination=f"{command.user_id}/{media_id}/{command.filename}",
            content_type=content_type,
        )
        return UploadResult(destination_path=metadata["path"], metadata=metadata)


__all__ = ["FakeStorageUploader", "FakeStorageUploadAdapter"]
