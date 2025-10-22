# src/sentiment_analysis/application/sentiment_analysis_service.py
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.sentiment_analysis.domain.interfaces import (
    ISentimentAnalyzer,
    ISentimentAnalysisRepository,
    ISentimentAnalysisTaskScheduler,
    SentimentOperationLogger,
    SentimentMetrics
)
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult # Importar a entidade

logger = structlog.get_logger(__name__)


class SentimentAnalysisService:
    """Application service for orchestrating sentiment analysis operations."""

    def __init__(
        self,
        sentiment_analyzer: ISentimentAnalyzer,
        sentiment_analysis_repo: ISentimentAnalysisRepository,
        task_scheduler: ISentimentAnalysisTaskScheduler,
        sentiment_logger: SentimentOperationLogger,
        sentiment_metrics: SentimentMetrics
    ):
        self.sentiment_analyzer = sentiment_analyzer
        self.sentiment_analysis_repo = sentiment_analysis_repo
        self.task_scheduler = task_scheduler
        self.sentiment_logger = sentiment_logger
        self.sentiment_metrics = sentiment_metrics

    async def request_sentiment_analysis(self, media_id: UUID, text_content: str, provider: str, language: str) -> Dict[str, Any]:
        """Requests the sentiment analysis of a text for a given media item."""
        logger.info(
            "sentiment_analysis_service.request_sentiment_analysis",
            media_id=str(media_id),
            provider=provider,
            language=language
        )
        try:
            # 1. Schedule the sentiment analysis task
            task_result = await self.task_scheduler.schedule_sentiment_analysis_task(
                media_id=str(media_id),
                text_content=text_content,
                provider=provider,
                language=language
            )

            logger.info(
                "sentiment_analysis_service.sentiment_analysis_scheduled",
                media_id=str(media_id),
                task_id=task_result.get("task_id")
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Sentiment analysis task scheduled successfully"
            }
        except Exception as e:
            logger.error(
                "sentiment_analysis_service.request_sentiment_analysis_failed",
                media_id=str(media_id),
                error=str(e)
            )
            raise

    async def get_sentiment_analysis_result(self, media_id: UUID) -> Optional[SentimentAnalysisResult]:
        """Retrieves a sentiment analysis result by its associated media ID."""
        return await self.sentiment_analysis_repo.get_by_media_id(media_id)

    async def get_sentiment_analysis_result_by_id(self, result_id: UUID) -> Optional[SentimentAnalysisResult]:
        """Retrieves a sentiment analysis result by its ID."""
        return await self.sentiment_analysis_repo.get_by_id(result_id)
