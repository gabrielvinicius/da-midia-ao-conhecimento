import structlog
from uuid import UUID
from typing import Any, Dict, Optional
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.signals import worker_process_init

from src.media_processing.application.worker_bootstrap import (
    build_text_extraction_service,
    build_transcription_service,
    build_video_processing_service,
)
from src.media_processing.application.worker import MediaWorkerApp
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

# Global event bus instance for the worker process
_WORKER_EVENT_BUS = None


def _ensure_event_bus(bus=None):
    global _WORKER_EVENT_BUS
    # If a global/singleton bus is needed, get_event_bus handles it
    if bus:
        return get_event_bus(bus)
    
    if _WORKER_EVENT_BUS:
        return _WORKER_EVENT_BUS

    return build_event_bus()


@worker_process_init.connect
def setup_worker_subscribers(**kwargs):
    """Initialize event subscribers when a worker process starts."""
    global _WORKER_EVENT_BUS
    logger.info("media_processing.worker.init")
    try:
        # Use the singleton event bus for this process
        _WORKER_EVENT_BUS = build_event_bus()
        app = MediaWorkerApp(event_bus=_WORKER_EVENT_BUS)
        app.ensure_subscribers()
        logger.info("media_processing.worker.subscribers_configured")
    except Exception as exc:
        logger.error("media_processing.worker.init_failed", error=str(exc))


async def _run_with_session(coro_factory):
    async with AsyncSessionLocal() as session:
        return await coro_factory(session)


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
        queue = "text_analysis_queue"
        task = process_text_extraction_task.apply_async(
            kwargs={
                "media_id": str(media_id),
                "file_path": file_path,
                "storage_provider": storage_provider,
                "user_id": user_id,
                "filename": filename,
                "triggered_by": triggered_by,
                "actor_id": actor_id,
                "correlation_id": correlation_id or str(media_id),
            },
            queue=queue
        )
        logger.info(
            "celery_task_scheduler.text_extraction_scheduled",
            media_id=str(media_id),
            task_id=task.id,
            queue=queue,
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
        
        # Simple heuristic: < 50MB goes to fast lane
        queue = "transcription_queue"
        if file_size_bytes and file_size_bytes < 50 * 1024 * 1024:
            queue = "transcription_fast_lane"

        task = process_transcription_task.apply_async(
            kwargs={
                "media_id": str(media_id),
                "file_path": file_path,
                "storage_provider": storage_provider,
                "transcription_provider": transcription_provider,
                "transcription_id": str(transcription_id),
                "language": language,
                "file_size_bytes": file_size_bytes,
                "summarization_provider": summarization_provider,
                "sentiment_provider": sentiment_provider,
                "topic_modeling_provider": topic_modeling_provider,
                "correlation_id": correlation_id or str(media_id),
                "user_id": user_id,
                "filename": filename,
                "triggered_by": triggered_by,
                "actor_id": actor_id,
            },
            queue=queue
        )
        logger.info(
            "celery_task_scheduler.transcription_task_scheduled",
            media_id=str(media_id),
            task_id=task.id,
            queue=queue,
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

        # Simple heuristic: < 50MB goes to fast lane
        queue = "video_queue"
        if file_size_bytes and file_size_bytes < 50 * 1024 * 1024:
            queue = "video_fast_lane"

        task = process_video_task.apply_async(
            kwargs={
                "media_id": media_id,
                "file_path": file_path,
                "storage_provider": storage_provider,
                "file_size_bytes": file_size_bytes,
                "user_id": user_id,
                "filename": filename,
                "triggered_by": triggered_by,
                "actor_id": actor_id,
                "correlation_id": correlation_id or media_id,
            },
            queue=queue
        )
        logger.info(
            "celery_task_scheduler.process_video_task_scheduled",
            media_id=media_id,
            task_id=task.id,
            queue=queue,
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
    final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
    async def _run():
        # Subscribers are bound at worker process init
        
        async with AsyncSessionLocal() as session:
            service = build_text_extraction_service(
                session=session,
                event_bus=_ensure_event_bus(),
                storage_provider=storage_provider,
            )
            await service.execute_text_extraction(
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                final_attempt=final_attempt,
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
    final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
    logger.info(
        "transcription.task_started",
        media_id=media_id,
        transcription_id=transcription_id,
    )

    async def _run():
        # Subscribers are bound at worker process init

        async with AsyncSessionLocal() as session:
            service = build_transcription_service(
                session=session,
                event_bus=_ensure_event_bus(),
                storage_provider=storage_provider,
            )

            return await service.execute_transcription(
                transcription_id=UUID(transcription_id),
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
                final_attempt=final_attempt,
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
            media_id=media_id,
            error=str(e),
            correlation_id=correlation_id,
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
    final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)

    async def _run():
        # Subscribers are bound at worker process init

        async with AsyncSessionLocal() as session:
            service = build_video_processing_service(
                session=session,
                event_bus=_ensure_event_bus(),
                storage_provider=storage_provider,
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
                final_attempt=final_attempt,
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
