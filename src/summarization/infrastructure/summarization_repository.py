# src/summarization/infrastructure/summarization_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.summarization.domain.summary import Summary


class SummarizationRepository:
    """SQLAlchemy implementation of the summarization repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, summary_id: UUID) -> Optional[Summary]:
        result = await self.db.execute(select(Summary).where(Summary.id == summary_id))
        return result.scalar_one_or_none()

    async def add(self, summary: Summary) -> None:
        self.db.add(summary)
        await self.db.flush()

    async def update(self, summary: Summary) -> None:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        await self.db.flush()

    async def get_by_media_id(self, media_id: UUID) -> Optional[Summary]:
        result = await self.db.execute(select(Summary).where(Summary.media_id == media_id))
        return result.scalar_one_or_none()

    async def delete_by_media_id(self, media_id: UUID) -> None:
        summary = await self.get_by_media_id(media_id)
        if summary is not None:
            await self.db.delete(summary)
            await self.db.flush()
