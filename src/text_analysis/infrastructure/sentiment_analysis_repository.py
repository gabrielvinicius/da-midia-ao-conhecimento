# src/sentiment_analysis/infrastructure/sentiment_analysis_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SentimentAnalysisRepository:
    """SQLAlchemy implementation of the sentiment analysis repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, result_id: UUID) -> Optional[SentimentAnalysisResult]:
        result = await self.db.execute(select(SentimentAnalysisResult).where(SentimentAnalysisResult.id == result_id))
        return result.scalar_one_or_none()

    async def add(self, result: SentimentAnalysisResult) -> None:
        self.db.add(result)
        await self.db.flush()

    async def update(self, result: SentimentAnalysisResult) -> None:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        await self.db.flush()

    async def get_by_media_id(self, media_id: UUID) -> Optional[SentimentAnalysisResult]:
        result = await self.db.execute(select(SentimentAnalysisResult).where(SentimentAnalysisResult.media_id == media_id))
        return result.scalar_one_or_none()