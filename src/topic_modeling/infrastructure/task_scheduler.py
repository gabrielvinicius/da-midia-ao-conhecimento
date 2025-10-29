# src/topic_modeling/infrastructure/task_scheduler.py
import structlog
from typing import Dict, Any, Optional

from src.text_analysis.tasks import process_topic_modeling_task

logger = structlog.get_logger(__name__)

class CeleryTopicModelingTaskScheduler:
    """Concrete implementation for scheduling topic modeling tasks using Celery."""

    async def schedule_topic_modeling_task(self, media_id: str, text_content: str, provider: str, language: str) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_topic_modeling_task",
            media_id=media_id,
            provider=provider,
            language=language
        )
        task = process_topic_modeling_task.delay(
            media_id=media_id,
            text_content=text_content,
            provider=provider,
            language=language
        )
        logger.info(
            "celery_task_scheduler.topic_modeling_task_scheduled",
            media_id=media_id,
            task_id=task.id
        )
        return {"task_id": task.id}
