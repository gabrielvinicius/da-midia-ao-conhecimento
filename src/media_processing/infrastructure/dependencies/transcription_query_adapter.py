from __future__ import annotations

from uuid import UUID

from src.media_processing.application.ports import TranscriptionQueryPort
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)


class TranscriptionQueryAdapter(TranscriptionQueryPort):
    """Expose transcription queries to text_analysis via media_processing repo."""

    def __init__(self, repo: TranscriptionRepository):
        self._repo = repo

    async def get_by_media_id(self, media_id: UUID):
        return await self._repo.get_by_media_id(media_id)

    async def get_by_id(self, transcription_id: UUID):
        return await self._repo.get_by_id(transcription_id)


__all__ = ["TranscriptionQueryAdapter"]
