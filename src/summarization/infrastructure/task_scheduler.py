import structlog
from typing import Dict, Any, Optional

from src.text_analysis.tasks import process_summarization_task

logger = structlog.get_logger(__name__)


class CelerySummarizationTaskScheduler:
    """Concrete implementation for scheduling summarization tasks using Celery."""

    async def schedule_summarization_task(self, media_id: str, text_content: str, provider: str, options: Optional[Dict[str, Any]] = None) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_summarization_task",
            media_id=media_id,
            provider=provider
        )
        task = process_summarization_task.delay(
            media_id=media_id,
            text_content=text_content,
            provider=provider,
            options=options
        )
        logger.info(
            "celery_task_scheduler.summarization_task_scheduled",
            media_id=media_id,
            task_id=task.id
        )
        return {"task_id": task.id}
