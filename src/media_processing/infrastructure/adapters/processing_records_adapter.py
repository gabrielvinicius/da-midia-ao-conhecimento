"""Responde ao módulo de mídias quais delas já têm registro de processamento."""
from __future__ import annotations

import datetime
from typing import List, Set
from uuid import UUID

from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)


class ProcessingRecordsAdapter:
    """ProcessingRecordsPort (media_management) sobre as transcrições deste módulo."""

    def __init__(self, repo: TranscriptionRepository):
        self._repo = repo

    async def media_with_processing(self, media_ids: List[UUID]) -> Set[UUID]:
        return await self._repo.media_ids_with_records(media_ids)

    async def media_with_finished_processing(
        self, media_ids: List[UUID], finished_before: datetime.datetime
    ) -> Set[UUID]:
        return await self._repo.media_ids_finished_before(media_ids, finished_before)


__all__ = ["ProcessingRecordsAdapter"]
