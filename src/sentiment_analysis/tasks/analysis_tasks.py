# src/sentiment_analysis/tasks/analysis_tasks.py
import asyncio
import structlog
from celery import shared_task
from uuid import UUID

from src.shared.infrastructure.database import get_db
from src.sentiment_analysis.infrastructure.dependencies import get_sentiment_analysis_service, get_topic_modeling_service
from src.sentiment_analysis.infrastructure.analysis_repository import AnalysisRepository
from src.sentiment_analysis.domain.analysis import Analysis, AnalysisType

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_sentiment_task(self, media_id: str, text_content: str):
    """Celery task to perform sentiment analysis on a block of text."""
    try:
        return asyncio.run(_run_sentiment_analysis(media_id, text_content))
    except Exception as e:
        logger.error("sentiment_analysis.task.failed", media_id=media_id, error=str(e), exc_info=True)
        return None

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_topics_task(self, media_id: str, text_content: str):
    """Celery task to perform topic modeling on a block of text."""
    try:
        return asyncio.run(_run_topic_modeling(media_id, text_content))
    except Exception as e:
        logger.error("topic_modeling.task.failed", media_id=media_id, error=str(e), exc_info=True)
        return None

async def _run_sentiment_analysis(media_id: str, text_content: str):
    """Helper to run sentiment analysis logic with manual dependency injection."""
    logger.info("sentiment_analysis.run.started", media_id=media_id)
    sentiment_service = get_sentiment_analysis_service()
    async for db_session in get_db():
        analysis_repo = AnalysisRepository(db_session)
        analysis_result = sentiment_service.analyze(text_content)
        analysis_entry = Analysis(media_id=UUID(media_id), type=AnalysisType.SENTIMENT, result=analysis_result)
        await analysis_repo.save(analysis_entry)
        logger.info("sentiment_analysis.run.completed", media_id=media_id, sentiment=analysis_result.get("label"))

async def _run_topic_modeling(media_id: str, text_content: str):
    """Helper to run topic modeling logic with manual dependency injection."""
    logger.info("topic_modeling.run.started", media_id=media_id)
    topic_service = get_topic_modeling_service()
    async for db_session in get_db():
        analysis_repo = AnalysisRepository(db_session)
        topics = topic_service.extract_topics(text_content)
        analysis_entry = Analysis(media_id=UUID(media_id), type=AnalysisType.TOPIC_MODELING, result={"topics": topics})
        await analysis_repo.save(analysis_entry)
        logger.info("topic_modeling.run.completed", media_id=media_id, num_topics=len(topics))
