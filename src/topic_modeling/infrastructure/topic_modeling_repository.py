# src/topic_modeling/infrastructure/topic_modeling_repository.py
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.topic_modeling.domain.topic_modeling import TopicModelingResult


class TopicModelingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, result: TopicModelingResult) -> TopicModelingResult:
        """Saves a topic modeling result to the database."""
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def find_by_media_id(self, media_id: str) -> Optional[TopicModelingResult]:
        """Finds a topic modeling result by its associated media ID."""
        result = await self.db.execute(
            select(TopicModelingResult).where(TopicModelingResult.media_id == UUID(media_id))
        )
        return result.scalar_one_or_none()
