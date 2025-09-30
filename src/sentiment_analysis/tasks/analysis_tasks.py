# src/sentiment_analysis/tasks/analysis_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.shared.events.event_bus import get_event_bus
from src.sentiment_analysis.application.commands.analyze_sentiment_command import AnalyzeSentimentCommand
from src.sentiment_analysis.application.commands.analyze_sentiment_command_handler import AnalyzeSentimentCommandHandler
from src.sentiment_analysis.infrastructure.dependencies import create_sentiment_analysis_service
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_sentiment_task(self, media_id: str, text_content: str, provider: str = "huggingface"):
    """Celery task to trigger the sentiment analysis pipeline."""
    try:
        return asyncio.run(_run_sentiment_analysis(media_id, text_content, provider))
    except Exception as e:
        logger.error(f"Error in sentiment analysis task for media {media_id}: {str(e)}", exc_info=True)
        return None

async def _run_sentiment_analysis(media_id: str, text_content: str, provider: str):
    """Helper to run sentiment analysis logic with manual dependency injection."""
    logger.info("sentiment_analysis.task.started", media_id=media_id)
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        event_bus = get_event_bus()
        repository = SentimentAnalysisRepository(db=db_session)
        service_factory = create_sentiment_analysis_service

        handler = AnalyzeSentimentCommandHandler(
            sentiment_service_factory=service_factory,
            repository=repository,
            event_bus=event_bus
        )

        command = AnalyzeSentimentCommand(
            media_id=media_id,
            text_content=text_content,
            provider=provider
        )

        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing sentiment analysis for media {media_id}: {str(e)}", exc_info=True)
            raise
