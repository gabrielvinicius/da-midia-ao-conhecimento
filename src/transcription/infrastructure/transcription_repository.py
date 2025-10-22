# src/transcription/infrastructure/transcription_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from src.transcription.domain.interfaces import ITranscriptionRepository
from src.transcription.domain.transcription import Transcription


class TranscriptionRepository(ITranscriptionRepository):
    """SQLAlchemy implementation of the transcription repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        result = await self.db.execute(select(Transcription).where(Transcription.id == transcription_id))
        return result.scalar_one_or_none()

    async def add(self, transcription: Transcription) -> None:
        self.db.add(transcription)
        await self.db.flush()

    async def update(self, transcription: Transcription) -> None:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        await self.db.flush()

    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        result = await self.db.execute(select(Transcription).where(Transcription.media_id == media_id))
        return result.scalar_one_or_none()