# src/text_processing/infrastructure/task_scheduler.py
import structlog
from typing import Dict, Any, Optional

from src.text_processing.domain.interfaces import ITextProcessingTaskScheduler
from src.text_processing.tasks.text_tasks import process_text_task

logger = structlog.get_logger(__name__)


class CeleryTextProcessingTaskScheduler(ITextProcessingTaskScheduler):
    """Concrete implementation for scheduling text processing tasks using Celery."""

    async def schedule_process_text_task(self, media_id: str, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_process_text_task",
            media_id=media_id,
            processing_type=processing_type
        )
        # Chamar a tarefa Celery
        task = process_text_task.delay(
            media_id=media_id,
            text_content=text_content,
            processing_type=processing_type,
            options=options
        )
        logger.info(
            "celery_task_scheduler.process_text_task_scheduled",
            media_id=media_id,
            task_id=task.id
        )
        return {"task_id": task.id}
