# src/sentiment_analysis/infrastructure/sentiment_analysis_repository.py
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult


class SentimentAnalysisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, result: SentimentAnalysisResult) -> SentimentAnalysisResult:
        """Saves a sentiment analysis result to the database."""
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def find_by_media_id(self, media_id: str) -> Optional[SentimentAnalysisResult]:
        """Finds a sentiment analysis result by its associated media ID."""
        result = await self.db.execute(
            select(SentimentAnalysisResult).where(SentimentAnalysisResult.media_id == UUID(media_id))
        )
        return result.scalar_one_or_none()
