# src/video_processing/infrastructure/task_scheduler.py
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CeleryVideoProcessingTaskScheduler:
    """Concrete implementation for scheduling video processing tasks using Celery."""

    async def schedule_process_video_task(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
        file_size_bytes: int | None = None,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_process_video_task",
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            file_size_bytes=file_size_bytes,
        )
        from src.media_processing.tasks import process_video_task

        task = process_video_task.delay(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            file_size_bytes=file_size_bytes,
        )
        logger.info(
            "celery_task_scheduler.process_video_task_scheduled",
            media_id=media_id,
            task_id=task.id,
        )
        return {"task_id": task.id}
