# src/transcription/infrastructure/transcription_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_processing.domain import Transcription
from src.media_processing.infrastructure.persistence.models import TranscriptionModel


class TranscriptionRepository:
    """SQLAlchemy implementation of the transcription repository."""

    def __init__(self, db):
        self.db = db

    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(TranscriptionModel).where(
                    TranscriptionModel.id == transcription_id
                )
            )
            model = result.scalar_one_or_none()
            return model.to_domain() if model else None
        else:  # It's a sync session
            return self.get_by_id_sync(transcription_id)

    def get_by_id_sync(self, transcription_id: UUID) -> Optional[Transcription]:
        stmt = select(TranscriptionModel).where(
            TranscriptionModel.id == transcription_id
        )
        result = self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def add(self, transcription: Transcription) -> None:
        model = TranscriptionModel.from_domain(transcription)
        if isinstance(self.db, AsyncSession):
            self.db.add(model)
            await self.db.commit() # Flush + Commit
            await self.db.refresh(model)
            transcription.id = model.id
        else:  # It's a sync session
            self.add_sync(transcription)

    def add_sync(self, transcription: Transcription) -> Transcription:
        model = TranscriptionModel.from_domain(transcription)
        self.db.add(model)
        self.db.commit() # Flush + Commit
        self.db.refresh(model)
        transcription.id = model.id
        return transcription

    async def update(self, transcription: Transcription) -> None:
        model = TranscriptionModel.from_domain(transcription)
        if isinstance(self.db, AsyncSession):
            await self.db.merge(model)
            await self.db.commit() # Flush + Commit
        else:  # It's a sync session
            self.update_sync(transcription)

    def update_sync(self, transcription: Transcription) -> Transcription:
        model = TranscriptionModel.from_domain(transcription)
        self.db.merge(model)
        self.db.commit() # Flush + Commit
        return transcription

    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(TranscriptionModel).where(
                    TranscriptionModel.media_id == media_id
                )
            )
            model = result.scalar_one_or_none()
            return model.to_domain() if model else None
        else:  # It's a sync session
            return self.get_by_media_id_sync(media_id)

    def get_by_media_id_sync(self, media_id: UUID) -> Optional[Transcription]:
        stmt = select(TranscriptionModel).where(
            TranscriptionModel.media_id == media_id
        )
        result = self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def delete_by_media_id(self, media_id: UUID) -> None:
        if isinstance(self.db, AsyncSession):
            stmt = select(TranscriptionModel).where(
                TranscriptionModel.media_id == media_id
            )
            result = await self.db.execute(stmt)
            for entity in result.scalars().all():
                await self.db.delete(entity)
            await self.db.commit()
        else:
            self.delete_by_media_id_sync(media_id)

    def delete_by_media_id_sync(self, media_id: UUID) -> None:
        stmt = select(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        result = self.db.execute(stmt)
        for entity in result.scalars().all():
            self.db.delete(entity)
        self.db.commit()
