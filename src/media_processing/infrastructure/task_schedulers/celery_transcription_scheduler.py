# src/media_processing/infrastructure/task_schedulers/celery_transcription_scheduler.py
from typing import Any, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class CeleryTranscriptionTaskScheduler:
    """Concrete implementation for scheduling transcription tasks using Celery."""

    async def schedule_transcription(
        self,
        transcription_id: UUID,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        file_size_bytes: int | None = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_transcription",
            media_id=str(media_id),
            transcription_id=str(transcription_id),
            provider=transcription_provider
        )
        from src.media_processing.application.tasks import process_transcription_task

        task = process_transcription_task.delay(
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            transcription_id=str(transcription_id),
            language=language,
            file_size_bytes=file_size_bytes,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
        )
        logger.info(
            "celery_task_scheduler.transcription_task_scheduled",
            media_id=str(media_id),
            task_id=task.id,
        )
        return {"task_id": task.id}