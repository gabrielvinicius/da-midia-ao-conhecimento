from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from asgiref.sync import async_to_sync
from celery import shared_task

from src.media_processing.application.worker_bootstrap import (
    build_text_extraction_service,
    build_transcription_service,
    build_video_processing_service,
)
from src.media_processing.infrastructure.dependencies.providers import get_event_bus
from src.shared.events.integration_events import (
    TASK_MEDIA_TEXT_EXTRACTION,
    TASK_MEDIA_TRANSCRIPTION,
    TASK_MEDIA_VIDEO_PROCESSING,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.event_bus_factory import (
    get_event_bus as build_event_bus,
)
logger = structlog.get_logger(__name__)

EVENT_BUS = build_event_bus()


def _ensure_event_bus(bus=None):
    return get_event_bus(bus or EVENT_BUS)


# --- Celery task schedulers (kept close to tasks for simplicity) ----------


class CeleryTextTaskScheduler:
    """Schedule text extraction tasks using Celery."""

    async def schedule_text_extraction(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        user_id: str | None = None,
        filename: str | None = None,
        triggered_by: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_text_extraction",
            media_id=str(media_id),
            file_path=file_path,
        )
        task = process_text_extraction_task.delay(
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=storage_provider,
            user_id=user_id,
            filename=filename,
            triggered_by=triggered_by,
            actor_id=actor_id,
            correlation_id=correlation_id or str(media_id),
        )
        logger.info(
            "celery_task_scheduler.text_extraction_scheduled",
            media_id=str(media_id),
            task_id=task.id,
        )
        return {"task_id": task.id}


class CeleryTranscriptionTaskScheduler:
    """Schedule transcription tasks using Celery."""

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
        user_id: Optional[str] = None,
        filename: Optional[str] = None,
        triggered_by: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_transcription",
            media_id=str(media_id),
            transcription_id=str(transcription_id),
            provider=transcription_provider,
        )
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
            correlation_id=correlation_id or str(media_id),
            user_id=user_id,
            filename=filename,
            triggered_by=triggered_by,
            actor_id=actor_id,
        )
        logger.info(
            "celery_task_scheduler.transcription_task_scheduled",
            media_id=str(media_id),
            task_id=task.id,
        )
        return {"task_id": task.id}


class CeleryVideoProcessingTaskScheduler:
    """Schedule video processing tasks using Celery."""

    async def schedule_process_video_task(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
        file_size_bytes: int | None = None,
        user_id: str | None = None,
        filename: str | None = None,
        triggered_by: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> Any:
        logger.info(
            "celery_task_scheduler.scheduling_process_video_task",
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            file_size_bytes=file_size_bytes,
        )
        task = process_video_task.delay(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            file_size_bytes=file_size_bytes,
            user_id=user_id,
            filename=filename,
            triggered_by=triggered_by,
            actor_id=actor_id,
            correlation_id=correlation_id or media_id,
        )
        logger.info(
            "celery_task_scheduler.process_video_task_scheduled",
            media_id=media_id,
            task_id=task.id,
        )
        return {"task_id": task.id}


def bootstrap_transcription_service(
    session, event_bus, storage_provider: str = "local"
):
    # Mantido por compatibilidade com schedulers; usa builder centralizado
    service = build_transcription_service(
        session=session,
        event_bus=event_bus,
        storage_provider=storage_provider,
    )
    # Reassocia scheduler específico de Celery
    service.task_scheduler = CeleryTranscriptionTaskScheduler()
    return service

def bootstrap_text_extraction_service(
    session, event_bus, storage_provider: str = "local"
):
    return build_text_extraction_service(
        session=session,
        event_bus=event_bus,
        storage_provider=storage_provider,
    )

def bootstrap_video_processing_service(
    session, event_bus, storage_provider: str = "local"
):
    return build_video_processing_service(
        session=session,
        event_bus=event_bus,
        storage_provider=storage_provider,
    )

@shared_task(
    bind=True,
    name=TASK_MEDIA_TEXT_EXTRACTION,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5
)
def process_text_extraction_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    user_id: Optional[str] = None,
    filename: Optional[str] = None,
    triggered_by: Optional[str] = None,
    actor_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> None:
    logger.info("text_extraction.task_started", media_id=media_id)
    async def _run():
        async with AsyncSessionLocal() as session:
            bus = _ensure_event_bus()
            service = bootstrap_text_extraction_service(
                session,
                bus,
                storage_provider,
            )
            await service.execute_text_extraction(
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                correlation_id=correlation_id,
                user_id=user_id,
                filename=filename,
            )
    try:
        async_to_sync(_run)()
    except Exception as e:
        logger.error("text_extraction.task_failed", error=str(e), media_id=media_id)
        raise

@shared_task(
    bind=True,
    name=TASK_MEDIA_TRANSCRIPTION,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5
)
def process_transcription_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    transcription_provider: str,
    transcription_id: str,
    language: str = "en",
    file_size_bytes: Optional[int] = None,
    summarization_provider: Optional[str] = None,
    sentiment_provider: Optional[str] = None,
    topic_modeling_provider: Optional[str] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    filename: Optional[str] = None,
    triggered_by: Optional[str] = None,
    actor_id: Optional[str] = None,
    **kwargs,
) -> Optional[Dict[str, Any]]:
    correlation_id = correlation_id or media_id
    logger.info(
        "transcription.task_started",
        media_id=media_id,
        transcription_id=transcription_id,
    )

    async def _run():
        async with AsyncSessionLocal() as session:
            bus = _ensure_event_bus()
            service = bootstrap_transcription_service(
                session,
                bus,
                storage_provider,
            )

            return await service.execute_transcription(
                transcription_id=UUID(transcription_id),
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
                summarization_provider=summarization_provider,
                sentiment_provider=sentiment_provider,
                topic_modeling_provider=topic_modeling_provider,
                correlation_id=correlation_id,
            )

    try:
        result = async_to_sync(_run)()
        return result
    except Exception as e:
        logger.error(
            "transcription.task_failed",
            extra={
                "media_id": media_id,
                "error": str(e),
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        raise

@shared_task(
    bind=True,
    name=TASK_MEDIA_VIDEO_PROCESSING,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_video_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str = "local",
    file_size_bytes: Optional[int] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    filename: Optional[str] = None,
    triggered_by: Optional[str] = None,
    actor_id: Optional[str] = None,
    **kwargs,
):
    logger.info(
        "video_processing.task_started",
        media_id=media_id,
        storage_provider=storage_provider,
    )

    async def _run():
        async with AsyncSessionLocal() as session:
            bus = _ensure_event_bus()
            service = bootstrap_video_processing_service(
                session,
                bus,
                storage_provider,
            )
            return await service.process_video_job(
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                file_size_bytes=file_size_bytes,
                correlation_id=correlation_id,
                user_id=user_id,
                filename=filename,
                triggered_by=triggered_by,
                actor_id=actor_id,
            )

    try:
        return async_to_sync(_run)()
    except Exception as e:
        logger.error(
            "video_processing.task_failed",
            media_id=media_id,
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise
