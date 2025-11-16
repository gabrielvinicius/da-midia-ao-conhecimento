# src/transcription/infrastructure/transcription_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.media_processing.transcription.domain.transcription import Transcription


class TranscriptionRepository:
    """SQLAlchemy implementation of the transcription repository."""

    def __init__(self, db):
        self.db = db

    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(Transcription).where(Transcription.id == transcription_id))
            return result.scalar_one_or_none()
        else:  # It's a sync session
            return self.get_by_id_sync(transcription_id)

    def get_by_id_sync(self, transcription_id: UUID) -> Optional[Transcription]:
        stmt = select(Transcription).where(Transcription.id == transcription_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, transcription: Transcription) -> None:
        if isinstance(self.db, AsyncSession):
            self.db.add(transcription)
            await self.db.flush()
        else:  # It's a sync session
            self.add_sync(transcription)

    def add_sync(self, transcription: Transcription) -> Transcription:
        self.db.add(transcription)
        self.db.flush()
        # Refresh to get the newly assigned ID
        self.db.refresh(transcription)
        return transcription

    async def update(self, transcription: Transcription) -> None:
        if isinstance(self.db, AsyncSession):
            # For SQLAlchemy, just adding to session and flushing is usually enough for updates
            # if the object is already tracked or has a primary key.
            await self.db.flush()
        else:  # It's a sync session
            self.update_sync(transcription)

    def update_sync(self, transcription: Transcription) -> Transcription:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        self.db.flush()
        # Refresh to get the latest state from DB
        self.db.refresh(transcription)
        return transcription

    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(Transcription).where(Transcription.media_id == media_id))
            return result.scalar_one_or_none()
        else:  # It's a sync session
            return self.get_by_media_id_sync(media_id)

    def get_by_media_id_sync(self, media_id: UUID) -> Optional[Transcription]:
        stmt = select(Transcription).where(Transcription.media_id == media_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
