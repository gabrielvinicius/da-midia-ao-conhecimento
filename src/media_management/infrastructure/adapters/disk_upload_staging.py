"""Envios em partes guardados em disco: ``<id>.part`` (os bytes) e ``<id>.json``
(nome, tamanho, dono), até a conclusão ou o prazo de abandono."""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import tempfile
from contextlib import suppress
from typing import AsyncIterator, Optional
from uuid import UUID

from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import StagedUpload


class DiskUploadStaging:
    def __init__(self, root_dir: str = "") -> None:
        self._root = root_dir or os.path.join(tempfile.gettempdir(), "envios-em-partes")

    def file_path(self, upload_id: UUID) -> str:
        return os.path.join(self._root, f"{upload_id}.part")

    def _meta_path(self, upload_id: UUID) -> str:
        return os.path.join(self._root, f"{upload_id}.json")

    async def create(self, upload: StagedUpload) -> None:
        def _create() -> None:
            os.makedirs(self._root, exist_ok=True)
            open(self.file_path(upload.upload_id), "wb").close()
            meta = {
                "user_id": upload.user_id,
                "filename": upload.filename,
                "size_bytes": upload.size_bytes,
                "storage_provider": upload.storage_provider,
                "transcription_provider": upload.transcription_provider,
                "created_at": upload.created_at.isoformat(),
            }
            with open(self._meta_path(upload.upload_id), "w", encoding="utf-8") as fh:
                json.dump(meta, fh)

        await asyncio.to_thread(_create)

    def _read(self, upload_id: UUID) -> Optional[StagedUpload]:
        try:
            with open(self._meta_path(upload_id), encoding="utf-8") as fh:
                meta = json.load(fh)
            received = os.path.getsize(self.file_path(upload_id))
        except (FileNotFoundError, ValueError):
            return None
        return StagedUpload(
            upload_id=upload_id,
            user_id=meta["user_id"],
            filename=meta["filename"],
            size_bytes=meta["size_bytes"],
            storage_provider=meta["storage_provider"],
            transcription_provider=meta["transcription_provider"],
            created_at=datetime.datetime.fromisoformat(meta["created_at"]),
            received_bytes=received,
        )

    async def get(self, upload_id: UUID) -> Optional[StagedUpload]:
        return await asyncio.to_thread(self._read, upload_id)

    async def write(self, upload_id: UUID, offset: int, chunks: AsyncIterator[bytes], max_bytes: int) -> int:
        target = await asyncio.to_thread(open, self.file_path(upload_id), "r+b")
        written = 0
        try:
            # Uma parte repetida regrava o mesmo trecho; o que vinha depois dele
            # (o resto de uma tentativa interrompida) é descartado.
            await asyncio.to_thread(target.truncate, offset)
            target.seek(offset)
            async for chunk in chunks:
                written += len(chunk)
                if written > max_bytes:
                    raise InvalidUploadError("A parte ultrapassa o tamanho permitido ou o tamanho do arquivo.")
                await asyncio.to_thread(target.write, chunk)
        finally:
            await asyncio.to_thread(target.close)
        return offset + written

    async def remove(self, upload_id: UUID) -> None:
        def _remove() -> None:
            for path in (self.file_path(upload_id), self._meta_path(upload_id)):
                with suppress(FileNotFoundError):
                    os.remove(path)

        await asyncio.to_thread(_remove)

    async def remove_created_before(self, moment: datetime.datetime) -> int:
        def _expired() -> list[UUID]:
            if not os.path.isdir(self._root):
                return []
            expired = []
            for name in os.listdir(self._root):
                stem, ext = os.path.splitext(name)
                if ext != ".json":
                    continue
                with suppress(ValueError):
                    staged = self._read(UUID(stem))
                    if staged and staged.created_at < moment:
                        expired.append(staged.upload_id)
            return expired

        expired = await asyncio.to_thread(_expired)
        for upload_id in expired:
            await self.remove(upload_id)
        return len(expired)


__all__ = ["DiskUploadStaging"]
