"""Tarefas Celery do módulo (camada de montagem: liga serviços e adaptadores)."""
import structlog
from uuid import UUID
from typing import Any, Dict, Optional
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.signals import worker_process_init

from src.media_processing.worker_bootstrap import (
    build_stalled_processing_monitor,
    build_text_extraction_service,
    build_transcription_service,
    build_unstarted_media_recovery,
)
from src.media_processing.worker import MediaWorkerApp
from src.media_processing.infrastructure.dependencies.providers import get_event_bus
from src.shared.events.integration_events import (
    TASK_MEDIA_SWEEP_STALLED,
    TASK_MEDIA_TEXT_EXTRACTION,
    TASK_MEDIA_TRANSCRIPTION,
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


@shared_task(name=TASK_MEDIA_SWEEP_STALLED, ignore_result=True)
def sweep_stalled_processing_task() -> dict:
    """Periódica (Celery beat, fila leve): reenfileira as mídias que não
    começaram e marca como falha as que passaram do prazo."""

    async def _run():
        bus = _ensure_event_bus()
        async with AsyncSessionLocal() as session:
            recovery = await build_unstarted_media_recovery(session, bus).sweep()
        async with AsyncSessionLocal() as session:
            failed = await build_stalled_processing_monitor(session, bus).sweep()
        return {
            "requeued": recovery.requeued,
            "failed": failed + recovery.failed,
        }

    result = async_to_sync(_run)()
    if result["requeued"] or result["failed"]:
        logger.warning("stalled_monitor.sweep_done", **result)
    return result
