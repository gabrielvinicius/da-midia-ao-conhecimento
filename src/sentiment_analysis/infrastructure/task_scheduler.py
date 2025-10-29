import structlog
from typing import Dict, Any, Optional

from src.text_analysis.tasks import process_sentiment_analysis_task

logger = structlog.get_logger(__name__)


class CelerySentimentAnalysisTaskScheduler:
    """Concrete implementation for scheduling sentiment analysis tasks using Celery."""

    async def schedule_sentiment_analysis_task(self, transcription_id: str, text: str, provider: str, model: Optional[str] = None, media_id: Optional[str] = None, language: Optional[str] = None) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_sentiment_analysis_task",
            transcription_id=transcription_id,
            provider=provider
        )
        task = process_sentiment_analysis_task.delay(
            transcription_id=transcription_id,
            text=text,
            provider=provider,
            model=model,
            media_id=media_id,
            language=language
        )
        logger.info(
            "celery_task_scheduler.sentiment_analysis_task_scheduled",
            transcription_id=transcription_id,
            task_id=task.id
        )
        return {"task_id": task.id}
