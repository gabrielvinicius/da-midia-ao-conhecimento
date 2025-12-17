from __future__ import annotations

from uuid import UUID

from src.media_management.application.ports import TranscriptionCleanupPort
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)


class TranscriptionCleanupAdapter(TranscriptionCleanupPort):
    def __init__(self, repo: TranscriptionRepository):
        self._repo = repo

    async def delete_by_media_id(self, media_id: UUID) -> None:
        await self._repo.delete_by_media_id(media_id)


__all__ = ["TranscriptionCleanupAdapter"]
