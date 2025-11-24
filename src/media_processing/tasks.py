from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.media_processing.application.dispatch_repository import (
    DispatchRecord,
    MediaDispatchRepository,
)
from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.shared.event_bus import InMemoryEventBus
from src.shared.events.domain_events import TextContentReady
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.text_analysis.application.event_handlers import build_text_content_ready_handler
from src.text_analysis.application.services import TextAnalysisService

logger = structlog.get_logger(__name__)

_dispatch_repository = MediaDispatchRepository()

@dataclass
class _DispatchAction:
    name: str
    task: Any
    payload: Dict[str, Any]
    fatal: bool = False


def _build_dispatch_actions(context: DispatchRecord) -> list[_DispatchAction]:
    """Return the Celery tasks that should run for the given media."""
    normalized_type = (context.media_type or "").upper()
    actions: list[_DispatchAction] = []

    # Text documents follow a dedicated pipeline that bypasses transcription
    if normalized_type == "TEXT":
        from src.text_analysis.tasks import process_text_document_task  # lazy import

        actions.append(
            _DispatchAction(
                name="text",
                task=process_text_document_task,
                payload={
                    "media_id": str(context.media_id),
                    "file_path": context.file_path,
                    "storage_provider": context.storage_provider,
                    "extraction_method": "basic",
                    "language": context.language,
                    "summarization_provider": context.summarization_provider,
                    "sentiment_provider": context.sentiment_provider,
                    "topic_modeling_provider": context.topic_modeling_provider,
                },
                fatal=True,
            )
        )
        return actions

    # Default pipeline always executes transcription first
    actions.append(
        _DispatchAction(
            name="transcription",
            task=process_transcription_task,
            payload={
                "media_id": context.media_id,
                "file_path": context.file_path,
                "storage_provider": context.storage_provider,
                "transcription_provider": context.transcription_provider,
                "language": context.language,
                "file_size_bytes": context.file_size_bytes,
                "summarization_provider": context.summarization_provider,
                "sentiment_provider": context.sentiment_provider,
                "topic_modeling_provider": context.topic_modeling_provider,
            },
            fatal=True,
        )
    )

    # Video assets run after transcription but do not mark the media as failed
    if normalized_type == "VIDEO":
        actions.append(
            _DispatchAction(
                name="video",
                task=process_video_task,
                payload={
                    "media_id": context.media_id,
                    "file_path": context.file_path,
                    "storage_provider": context.storage_provider,
                    "file_size_bytes": context.file_size_bytes,
                },
                fatal=False,
            )
        )

    return actions


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_media_task(self, media_id: str) -> None:
    """Entry point that dispatches concrete processing tasks for a media item."""
    logger.info("media_processing.dispatch.started", media_id=media_id)

    try:
        media_uuid = UUID(str(media_id))
    except ValueError:
        logger.error("media_processing.dispatch.invalid_id", media_id=media_id)
        return

    try:
        context = _dispatch_repository.mark_processing(media_uuid)
    except Exception as exc:
        logger.error("media_processing.dispatch.db_error", media_id=media_id, error=str(exc), exc_info=True)
        raise

    if context is None:
        logger.warning("media_processing.dispatch.media_not_found", media_id=media_id)
        return

    if not context.file_path:
        reason = "missing file path for media"
        logger.error("media_processing.dispatch.missing_file_path", media_id=media_id)
        _dispatch_repository.mark_failed(media_uuid, reason)
        return

    actions = _build_dispatch_actions(context)
    if not actions:
        logger.info("media_processing.dispatch.no_actions", media_id=media_id)
        return

    for action in actions:
        try:
            action.task.delay(**action.payload)
            logger.info(
                "media_processing.dispatch.action_enqueued",
                media_id=media_id,
                action=action.name,
            )
        except ValidationError as exc:
            logger.error(
                f"media_processing.dispatch.{action.name}_payload_invalid",
                media_id=media_id,
                errors=exc.errors(),
            )
            if action.fatal:
                _dispatch_repository.mark_failed(media_uuid, f"invalid {action.name} payload")
                return
        except Exception as exc:
            logger.error(
                f"media_processing.dispatch.{action.name}_enqueue_failed",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )
            if action.fatal:
                _dispatch_repository.mark_failed(media_uuid, f"failed to enqueue {action.name} task")
                raise

    logger.info("media_processing.dispatch.completed", media_id=media_id)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_transcription_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    transcription_provider: str,
    language: str = "en",
    file_size_bytes: Optional[int] = None,
    summarization_provider: Optional[str] = None,
    sentiment_provider: Optional[str] = None,
    topic_modeling_provider: Optional[str] = None,
) -> Optional[str]:
    try:
        payload = TranscriptionTaskPayload.model_validate(
            {
                "media_id": media_id,
                "file_path": file_path,
                "storage_provider": storage_provider,
                "transcription_provider": transcription_provider,
                "language": language,
                "file_size_bytes": file_size_bytes,
                "summarization_provider": summarization_provider,
                "sentiment_provider": sentiment_provider,
                "topic_modeling_provider": topic_modeling_provider,
            }
        )
    except ValidationError as exc:
        logger.error(
            "transcription.task_invalid_media_id",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        # Use synchronous database session for celery tasks
        with get_sync_session() as db:
            return _execute_transcription_job_sync(
                db,
                payload=payload,
            )
    except Exception as e:
        logger.error(
            "transcription.task_failed",
            extra={
                "media_id": media_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def _execute_transcription_job_sync(
    db,
    *,
    payload: TranscriptionTaskPayload,
) -> Optional[str]:
    from src.media_processing.transcription.infrastructure.transcription_repository import (
        TranscriptionRepository,
    )
    from src.media_processing.transcription.infrastructure.task_scheduler import (
        CeleryTranscriptionTaskScheduler,
    )
    from src.media_processing.transcription.infrastructure.logging import (
        StructuredTranscriptionLogger,
    )
    from src.media_processing.transcription.infrastructure.metrics import (
        PrometheusTranscriptionMetrics,
    )
    from src.media_management.application.queries.media_queries import MediaQueries
    from src.media_management.infrastructure.media_repository import MediaRepository

    event_bus = InMemoryEventBus()
    text_analysis_service = TextAnalysisService()
    event_bus.subscribe(
        TextContentReady,
        build_text_content_ready_handler(text_analysis_service),
    )

    storage_factory = StorageServiceFactory()
    storage_adapter = storage_factory.create_storage_service(payload.storage_provider)

    transcription_repo = TranscriptionRepository(db)
    media_repo = MediaRepository(db=db)
    media_queries = MediaQueries(media_repository=media_repo)

    service = TranscriptionService(
        transcription_repo=transcription_repo,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=PrometheusTranscriptionMetrics(),
        storage_service=storage_adapter,
        speech_recognizer_factory=lambda: None,
        db_session=db,
        media_queries=media_queries,
        event_bus=event_bus,
    )

    # Execute the transcription job and handle potential database session issues
    try:
        result = service.process_transcription_job_sync(
            media_id=payload.media_id,
            file_path=payload.file_path,
            storage_provider=payload.storage_provider,
            transcription_provider=payload.transcription_provider,
            language=payload.language,
            summarization_provider=payload.summarization_provider,
            sentiment_provider=payload.sentiment_provider,
            topic_modeling_provider=payload.topic_modeling_provider,
        )
        
        # Commit any pending changes to the database
        try:
            db.commit()
        except Exception:
            # If there's an issue with commit, make sure to rollback but don't fail the whole process
            try:
                db.rollback()
            except Exception:
                pass  # Just suppress rollback errors
        
        return result
    except Exception as e:
        # If there's an issue during processing, rollback and re-raise
        try:
            db.rollback()
        except Exception:
            pass  # Just suppress rollback errors
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_video_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    file_size_bytes: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    try:
        payload = VideoTaskPayload.model_validate(
            {
                "media_id": media_id,
                "file_path": file_path,
                "storage_provider": storage_provider,
                "file_size_bytes": file_size_bytes,
            }
        )
    except ValidationError as exc:
        logger.error(
            "video_processing.task_invalid_payload",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        # Use synchronous database session for celery tasks
        with get_sync_session() as db:
            return _execute_video_processing_job_sync(
                db,
                payload=payload,
            )
    except Exception as e:
        logger.error(
            "video_processing.task_failed",
            extra={
                "media_id": media_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return None

def _execute_video_processing_job_sync(
    db,
    *,
    payload: VideoTaskPayload,
) -> Optional[Dict[str, Any]]:
    from src.media_processing.video_processing.bootstrap import (
        VideoProcessingContainer,
    )

    storage_factory = StorageServiceFactory()
    storage_adapter = storage_factory.create_storage_service(payload.storage_provider)

    # Create container with dependencies, using shared metrics to prevent duplicates
    container = VideoProcessingContainer(
        db=db,
        storage_factory=storage_factory,
        storage_provider=payload.storage_provider,
    )

    # Create the service manually to pass correct dependencies with sync methods
    video_audio_extractor = container.video_audio_extractor()
    video_thumbnail_generator = container.video_thumbnail_generator()
    video_processing_task_scheduler = container.video_processing_task_scheduler()
    video_processing_metrics = container.video_processing_metrics()

    service = container.video_processing_service(
        video_audio_extractor=video_audio_extractor,
        video_thumbnail_generator=video_thumbnail_generator,
        video_processing_task_scheduler=video_processing_task_scheduler,
        storage_factory=storage_factory,
        default_storage_provider=payload.storage_provider,
        video_processing_metrics=video_processing_metrics,
    )

    # Execute the video processing job and handle potential database session issues
    result = service.process_video_job_sync(
        media_id=payload.media_id,
        file_path=payload.file_path,
        storage_provider=payload.storage_provider,
        file_size_bytes=payload.file_size_bytes,
    )
    
    # Commit any pending changes to the database
    try:
        db.commit()
    except Exception:
        # If there's an issue with commit, make sure to rollback but don't fail the whole process
        try:
            db.rollback()
        except Exception:
            pass  # Just suppress rollback errors

    return result
