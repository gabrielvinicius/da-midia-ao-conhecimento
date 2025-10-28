# src/sentiment_analysis/application/queries/sentiment_analysis_queries.py
from typing import Optional

from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult
# FIXED: Application should not import Infrastructure directly
from src.shared.application.dependency_injection import get_sentiment_analysis_repository


class SentimentAnalysisQueries:
    """Handles all read-only operations for sentiment analysis results."""
    def __init__(self, repository: SentimentAnalysisRepository):
        self.repository = repository

    async def get_by_media_id(self, media_id: str) -> Optional[SentimentAnalysisResult]:
        """Retrieves a sentiment analysis result by its associated media ID."""
        return await self.repository.find_by_media_id(media_id)
