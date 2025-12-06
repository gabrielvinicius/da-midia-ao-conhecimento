# src/transcription/infrastructure/task_scheduler.py
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CeleryTranscriptionTaskScheduler:
    """Concrete implementation for scheduling transcription tasks using Celery."""

    async def schedule_transcription_task(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        file_size_bytes: int | None = None,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_transcription_task",
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language,
            file_size_bytes=file_size_bytes,
        )
        from src.media_processing.tasks import process_transcription_task

        task = process_transcription_task.delay(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language,
            file_size_bytes=file_size_bytes,
        )
        logger.info(
            "celery_task_scheduler.transcription_task_scheduled",
            media_id=media_id,
            task_id=task.id,
        )
        return {"task_id": task.id}
