from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.media_processing.application.ports import TranscriptionQueryPort
from src.media_processing.domain import Transcription


class TranscriptionReadService:
    """Read-side service for transcriptions (CQRS consulta)."""

    def __init__(self, queries: TranscriptionQueryPort) -> None:
        self._queries = queries

    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        return await self._queries.get_by_id(transcription_id)

    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        return await self._queries.get_by_media_id(media_id)


__all__ = ["TranscriptionReadService"]
