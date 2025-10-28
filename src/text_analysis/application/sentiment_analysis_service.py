# src/sentiment_analysis/application/sentiment_analysis_service.py
"""
Consolidated Sentiment Analysis Service.
"""
import time
from typing import Dict, Any, Optional
from uuid import UUID

import structlog
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult, SentimentLabel
from src.sentiment_analysis.infrastructure.logging import StructuredSentimentLogger
from src.sentiment_analysis.infrastructure.metrics import PrometheusSentimentMetrics
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository
from src.sentiment_analysis.infrastructure.sentiment_analyzer import HuggingFaceSentimentAnalyzer
from src.sentiment_analysis.infrastructure.task_scheduler import CelerySentimentAnalysisTaskScheduler

logger = structlog.get_logger(__name__)


class SentimentAnalysisService:
    """
    Consolidated service for all sentiment analysis operations.
    """
    
    def __init__(
        self,
        sentiment_analyzer: HuggingFaceSentimentAnalyzer,
        sentiment_analysis_repo: SentimentAnalysisRepository,
        task_scheduler: CelerySentimentAnalysisTaskScheduler,
        sentiment_logger: StructuredSentimentLogger,
        sentiment_metrics: PrometheusSentimentMetrics
    ):
        self.analyzer = sentiment_analyzer
        self.repo = sentiment_analysis_repo
        self.task_scheduler = task_scheduler
        self.logger = sentiment_logger
        self.metrics = sentiment_metrics

    async def analyze_sentiment(self, media_id: UUID, text_content: str, provider: str, language: str, options: Optional[Dict[str, Any]] = None) -> SentimentAnalysisResult:
        """Performs sentiment analysis on text content and saves the result."""
        start_time = time.monotonic()
        success = False
        error = None
        result_id = None
        output_score = 0.0

        logger.info("sentiment.analyze.started", media_id=str(media_id), provider=provider)
        try:
            # 1. Perform sentiment analysis
            analysis_data = await self.analyzer.analyze(
                text_content=text_content,
                language=language,
                options=options
            )
            output_score = analysis_data.get("score", 0.0)

            # 2. Create or update SentimentAnalysisResult entity
            existing_result = await self.repo.get_by_media_id(media_id)

            if existing_result:
                existing_result.update_from_analysis(analysis_data)
                await self.repo.update(existing_result)
                sentiment_result = existing_result
            else:
                sentiment_result = SentimentAnalysisResult(
                    media_id=media_id,
                    label=analysis_data.get("label"),
                    score=analysis_data.get("score"),
                    confidence=analysis_data.get("confidence"),
                    provider=analysis_data.get("provider"),
                    model_name=analysis_data.get("model_name"),
                    processing_time_ms=analysis_data.get("processing_time_ms"),
                    text_length=analysis_data.get("text_length"),
                    language=analysis_data.get("language"),
                    granularity=analysis_data.get("granularity"),
                    full_result=analysis_data.get("full_result"),
                    detailed_scores=analysis_data.get("detailed_scores"),
                    emotions=analysis_data.get("emotions"),
                    keywords=analysis_data.get("keywords"),
                    is_reliable=analysis_data.get("is_reliable", True),
                    error_message=analysis_data.get("error_message"),
                )
                await self.repo.add(sentiment_result)
            
            result_id = sentiment_result.id
            success = True

            logger.info("sentiment.analyze.completed", media_id=str(media_id), result_id=str(result_id))
            return sentiment_result

        except Exception as e:
            error = e
            logger.error("sentiment.analyze.failed", media_id=str(media_id), error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.logger.log_operation(
                operation="analyze_sentiment",
                media_id=str(media_id),
                provider=provider,
                success=success,
                duration=duration,
                error=error
            )
            await self.metrics.record_operation(
                operation="analyze_sentiment",
                provider=provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(text_content),
                output_score=output_score
            )

    async def request_sentiment_analysis(self, media_id: UUID, text_content: str, provider: str, language: str) -> Dict[str, Any]:
        """Requests the sentiment analysis of a text for a given media item by scheduling a task."""
        logger.info("sentiment.request.started", media_id=str(media_id), provider=provider)
        try:
            # In a real scenario, this would schedule an async task.
            # For now, we'll call the analysis directly.
            sentiment_result = await self.analyze_sentiment(media_id, text_content, provider, language)
            
            logger.info("sentiment.request.completed", media_id=str(media_id), result_id=str(sentiment_result.id))
            return {
                "success": True,
                "media_id": str(media_id),
                "result_id": str(sentiment_result.id),
                "message": "Sentiment analysis completed directly (or scheduled)"
            }
        except Exception as e:
            logger.error("sentiment.request.failed", media_id=str(media_id), error=str(e))
            raise

    async def get_sentiment_analysis_result(self, media_id: UUID) -> Optional[SentimentAnalysisResult]:
        """Retrieves a sentiment analysis result by its associated media ID."""
        return await self.repo.get_by_media_id(media_id)

    async def get_sentiment_analysis_result_by_id(self, result_id: UUID) -> Optional[SentimentAnalysisResult]:
        """Retrieves a sentiment analysis result by its ID."""
        return await self.repo.get_by_id(result_id)