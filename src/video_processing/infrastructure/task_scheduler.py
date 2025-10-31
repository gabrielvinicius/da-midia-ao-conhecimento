# src/video_processing/infrastructure/task_scheduler.py
from typing import Any

import structlog

from src.media_processing.tasks import process_video_task

logger = structlog.get_logger(__name__)


class CeleryVideoProcessingTaskScheduler:
    """Concrete implementation for scheduling video processing tasks using Celery."""

    async def schedule_process_video_task(self, media_id: str, file_path: str) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_process_video_task",
            media_id=media_id,
            file_path=file_path
        )
        task = process_video_task.delay(
            media_id=media_id,
            file_path=file_path
        )
        logger.info(
            "celery_task_scheduler.process_video_task_scheduled",
            media_id=media_id,
            task_id=task.id
        )
        return {"task_id": task.id}
