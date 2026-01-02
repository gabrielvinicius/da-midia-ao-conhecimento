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
from src.shared.domain.events import (
    MediaProcessingFailed,
    MediaProcessingStarted,
    TextContentReady,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.event_bus_factory import (
    get_event_bus as build_event_bus,
)
logger = structlog.get_logger(__name__)

EVENT_BUS = build_event_bus()


def _ensure_event_bus(bus=None):
    return get_event_bus(bus or EVENT_BUS)

_WORKER_SUBSCRIBERS_BOUND = False


def _bind_worker_subscribers(event_bus) -> None:
    """Registra subscribers no processo do worker (event bus é apenas in-process).

    Eventos publicados no worker não chegam ao processo da API. Logo, o worker
    precisa assinar handlers que atualizam estado e disparam os próximos passos.
    """

    global _WORKER_SUBSCRIBERS_BOUND
    if _WORKER_SUBSCRIBERS_BOUND:
        return

    # Adapters estáveis (evita registrar coletores Prometheus repetidamente).
    from src.notifications.infrastructure.adapters.notification_logger_adapter import (
        NotificationLoggerAdapter,
    )
    from src.notifications.infrastructure.adapters.notification_metrics_adapter import (
        NotificationMetricsAdapter,
    )
    from src.notifications.infrastructure.adapters.redis_notification_delivery_adapter import (
        RedisNotificationDeliveryAdapter,
    )

    notification_logger = NotificationLoggerAdapter()
    notification_metrics = NotificationMetricsAdapter()
    realtime_delivery = RedisNotificationDeliveryAdapter()

    async def _on_transcription_completed(event: TranscriptionCompleted) -> None:
        async with AsyncSessionLocal() as session:
            from src.media_management.infrastructure.dependencies.builders import (
                build_media_event_handlers,
            )
            from src.storage.infrastructure.dependencies import StorageServiceFactory
            from src.notifications.application.services.pipeline_notification_service import (
                PipelineNotificationService,
            )
            from src.notifications.infrastructure.adapters.notification_repository_adapter import (
                NotificationRepositoryAdapter,
            )
            from src.notifications.infrastructure.repositories.notification_repository import (
                NotificationRepository,
            )
            from uuid import UUID

            handlers = build_media_event_handlers(
                session=session,
                storage_factory=StorageServiceFactory(),
                event_bus=event_bus,
            )
            await handlers.handle_transcription_completed(event)

            if getattr(event, "user_id", None):
                repo = NotificationRepository(db=session)
                service = PipelineNotificationService(
                    notification_repo=NotificationRepositoryAdapter(repo),
                    delivery=realtime_delivery,
                    notification_logger=notification_logger,
                    notification_metrics=notification_metrics,
                )
                await service.notify(
                    user_id=UUID(str(event.user_id)),
                    message="Transcrição concluída com sucesso.",
                    correlation_id=getattr(event, "correlation_id", None),
                    variables={
                        "media_id": str(event.media_id),
                        "transcription_id": str(event.transcription_id),
                        "evento": "TranscriptionCompleted",
                    },
                )

    async def _on_transcription_failed(event: TranscriptionFailed) -> None:
        async with AsyncSessionLocal() as session:
            from src.media_management.infrastructure.dependencies.builders import (
                build_media_event_handlers,
            )
            from src.storage.infrastructure.dependencies import StorageServiceFactory
            from src.notifications.application.services.pipeline_notification_service import (
                PipelineNotificationService,
            )
            from src.notifications.infrastructure.adapters.notification_repository_adapter import (
                NotificationRepositoryAdapter,
            )
            from src.notifications.infrastructure.repositories.notification_repository import (
                NotificationRepository,
            )
            from uuid import UUID

            handlers = build_media_event_handlers(
                session=session,
                storage_factory=StorageServiceFactory(),
                event_bus=event_bus,
            )
            await handlers.handle_transcription_failed(event)

            if getattr(event, "user_id", None):
                repo = NotificationRepository(db=session)
                service = PipelineNotificationService(
                    notification_repo=NotificationRepositoryAdapter(repo),
                    delivery=realtime_delivery,
                    notification_logger=notification_logger,
                    notification_metrics=notification_metrics,
                )
                await service.notify(
                    user_id=UUID(str(event.user_id)),
                    message="Falha ao processar a transcrição.",
                    correlation_id=getattr(event, "correlation_id", None),
                    variables={
                        "media_id": str(event.media_id),
                        "transcription_id": (
                            str(event.transcription_id)
                            if getattr(event, "transcription_id", None)
                            else None
                        ),
                        "erro": getattr(event, "error_message", None),
                        "evento": "TranscriptionFailed",
                    },
                )

    async def _on_text_content_ready(event: TextContentReady) -> None:
        if not getattr(event, "text", None):
            return

        async with AsyncSessionLocal() as session:
            from src.media_management.infrastructure.dependencies.builders import (
                build_media_event_handlers,
            )
            from src.storage.infrastructure.dependencies import StorageServiceFactory

            handlers = build_media_event_handlers(
                session=session,
                storage_factory=StorageServiceFactory(),
                event_bus=event_bus,
            )
            await handlers.handle_text_content_ready(event)

        payload: Dict[str, Any] = {
            "media_id": str(event.media_id),
            "transcription_id": (
                str(event.transcription_id)
                if getattr(event, "transcription_id", None)
                else None
            ),
            "user_id": getattr(event, "user_id", None),
            "filename": getattr(event, "filename", None),
            "text_content": getattr(event, "text", None),
            "language": (
                (event.metadata or {}).get("language")
                if isinstance(getattr(event, "metadata", None), dict)
                else None
            ),
            "correlation_id": getattr(event, "correlation_id", None),
        }

        try:
            from src.text_analysis.tasks import analyze_task  # noqa: WPS433

            if hasattr(analyze_task, "delay"):
                analyze_task.delay(**payload)
            else:  # pragma: no cover
                analyze_task(**payload)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "text_analysis.enqueue_failed",
                media_id=str(event.media_id),
                error=str(exc),
            )

    async def _on_media_processing_started(event: MediaProcessingStarted) -> None:
        async with AsyncSessionLocal() as session:
            from src.media_management.infrastructure.dependencies.builders import (
                build_media_event_handlers,
            )
            from src.storage.infrastructure.dependencies import StorageServiceFactory

            handlers = build_media_event_handlers(
                session=session,
                storage_factory=StorageServiceFactory(),
                event_bus=event_bus,
            )
            await handlers.handle_media_processing_started(event)

    async def _on_media_processing_failed(event: MediaProcessingFailed) -> None:
        async with AsyncSessionLocal() as session:
            from src.media_management.infrastructure.dependencies.builders import (
                build_media_event_handlers,
            )
            from src.storage.infrastructure.dependencies import StorageServiceFactory
            from src.notifications.application.services.pipeline_notification_service import (
                PipelineNotificationService,
            )
            from src.notifications.infrastructure.adapters.notification_repository_adapter import (
                NotificationRepositoryAdapter,
            )
            from src.notifications.infrastructure.repositories.notification_repository import (
                NotificationRepository,
            )
            from uuid import UUID

            handlers = build_media_event_handlers(
                session=session,
                storage_factory=StorageServiceFactory(),
                event_bus=event_bus,
            )
            await handlers.handle_media_processing_failed(event)

            user_id = None
            if isinstance(getattr(event, "metadata", None), dict):
                user_id = event.metadata.get("user_id")
            if user_id:
                repo = NotificationRepository(db=session)
                service = PipelineNotificationService(
                    notification_repo=NotificationRepositoryAdapter(repo),
                    delivery=realtime_delivery,
                    notification_logger=notification_logger,
                    notification_metrics=notification_metrics,
                )
                await service.notify(
                    user_id=UUID(str(user_id)),
                    message="Falha durante o processamento do arquivo.",
                    correlation_id=getattr(event, "correlation_id", None),
                    variables={
                        "media_id": str(event.media_id),
                        "stage": getattr(event, "stage", None),
                        "erro": getattr(event, "error_message", None),
                        "evento": "MediaProcessingFailed",
                    },
                )

    event_bus.subscribe(TranscriptionCompleted, _on_transcription_completed)
    event_bus.subscribe(TranscriptionFailed, _on_transcription_failed)
    event_bus.subscribe(TextContentReady, _on_text_content_ready)
    event_bus.subscribe(MediaProcessingStarted, _on_media_processing_started)
    event_bus.subscribe(MediaProcessingFailed, _on_media_processing_failed)
    _WORKER_SUBSCRIBERS_BOUND = True


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
    final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
    async def _run():
        _bind_worker_subscribers(_ensure_event_bus())
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
        _bind_worker_subscribers(_ensure_event_bus())
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
        _bind_worker_subscribers(_ensure_event_bus())
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
