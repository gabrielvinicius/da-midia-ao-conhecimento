# src/media_processing/infrastructure/task_schedulers/celery_text_extraction_scheduler.py
from typing import Any
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

class CeleryTextTaskScheduler:
    """Concrete implementation for scheduling text extraction tasks using Celery."""

    async def schedule_text_extraction(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_text_extraction",
            media_id=str(media_id),
            file_path=file_path
        )
        from src.media_processing.application.tasks import process_text_extraction_task

        task = process_text_extraction_task.delay(
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=storage_provider,
        )
        logger.info(
            "celery_task_scheduler.text_extraction_scheduled",
            media_id=str(media_id),
            task_id=task.id,
        )
        return {"task_id": task.id}