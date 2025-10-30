# src/topic_modeling/infrastructure/topic_modeling_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any
from uuid import UUID

from src.topic_modeling.domain.topic_modeling import TopicModelingResult

class TopicModelingRepository:
    """SQLAlchemy implementation of the topic modeling repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, result_id: UUID) -> Optional[TopicModelingResult]:
        result = await self.db.execute(select(TopicModelingResult).where(TopicModelingResult.id == result_id))
        return result.scalar_one_or_none()

    async def add(self, result: TopicModelingResult) -> None:
        self.db.add(result)
        await self.db.flush()

    async def update(self, result: TopicModelingResult) -> None:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        await self.db.flush()

    async def get_by_media_id(self, media_id: UUID) -> Optional[TopicModelingResult]:
        result = await self.db.execute(select(TopicModelingResult).where(TopicModelingResult.media_id == media_id))
        return result.scalar_one_or_none()
