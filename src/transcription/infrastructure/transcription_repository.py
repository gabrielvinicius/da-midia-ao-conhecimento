# src/transcription/infrastructure/transcription_repository.py
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.transcription.domain.transcription import Transcription


class TranscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, transcription: Transcription) -> Transcription:
        self.db.add(transcription)
        await self.db.commit()
        await self.db.refresh(transcription)
        return transcription

    async def find_by_id(self, transcription_id: str) -> Optional[Transcription]:
        result = await self.db.execute(
            select(Transcription).where(Transcription.id == UUID(transcription_id))
        )
        return result.scalar_one_or_none()

    async def find_by_media_id(self, media_id: str) -> Optional[Transcription]:
        """Finds a transcription by its associated media ID."""
        result = await self.db.execute(
            select(Transcription).where(Transcription.media_id == UUID(media_id))
        )
        return result.scalar_one_or_none()
