from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.shared.event_bus import InMemoryEventBus
from src.shared.events.domain_events import TextContentReady
from src.shared.infrastructure.database import get_sync_session
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.text_analysis.application.event_handlers import build_text_content_ready_handler
from src.text_analysis.application.services import TextAnalysisService

logger = structlog.get_logger(__name__)

@dataclass
class _MediaDispatchContext:
    media_id: UUID
    file_path: str
    storage_provider: str
    transcription_provider: str
    language: str
    media_type: Optional[str]
    file_size_bytes: Optional[int]
    summarization_provider: Optional[str]
    sentiment_provider: Optional[str]
    topic_modeling_provider: Optional[str]


def _load_media_dispatch_context(media_uuid: UUID) -> Optional[_MediaDispatchContext]:
    from src.media_management.domain.enums import MediaStatus
    from src.media_management.infrastructure.orm.media_entity import MediaEntity

    with get_sync_session() as session:
        media: MediaEntity | None = session.get(MediaEntity, media_uuid)
        if media is None:
            return None

        media.status = MediaStatus.PROCESSING
        media.error_message = None
        session.flush()

        media_type_value = getattr(media, "media_type", None)
        if media_type_value is not None:
            media_type_value = getattr(media_type_value, "value", str(media_type_value))

        return _MediaDispatchContext(
            media_id=media_uuid,
            file_path=media.original_file_path or "",
            storage_provider=(media.storage_provider or "local"),
            transcription_provider=(media.transcription_provider or "fastwhisper"),
            language=media.language or "en",
            media_type=media_type_value,
            file_size_bytes=getattr(media, "file_size", None),
            summarization_provider=getattr(media, "summarization_provider", None),
            sentiment_provider=getattr(media, "sentiment_provider", None),
            topic_modeling_provider=getattr(media, "topic_modeling_provider", None),
        )


def _mark_media_failed(media_uuid: UUID, reason: str) -> None:
    truncated_reason = reason[:250]
    from src.media_management.domain.enums import MediaStatus
    from src.media_management.infrastructure.orm.media_entity import MediaEntity

    with get_sync_session() as session:
        media: MediaEntity | None = session.get(MediaEntity, media_uuid)
        if media is None:
            return
        media.status = MediaStatus.FAILED
        media.error_message = truncated_reason
        session.flush()


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
        context = _load_media_dispatch_context(media_uuid)
    except Exception as exc:
        logger.error("media_processing.dispatch.db_error", media_id=media_id, error=str(exc), exc_info=True)
        raise

    if context is None:
        logger.warning("media_processing.dispatch.media_not_found", media_id=media_id)
        return

    if not context.file_path:
        reason = "missing file path for media"
        logger.error("media_processing.dispatch.missing_file_path", media_id=media_id)
        _mark_media_failed(media_uuid, reason)
        return

    if (context.media_type or "").upper() == "TEXT":
        try:
            from src.text_analysis.tasks import process_text_document_task

            process_text_document_task.delay(
                media_id=str(context.media_id),
                file_path=context.file_path,
                storage_provider=context.storage_provider,
                extraction_method="basic",
                language=context.language,
                summarization_provider=context.summarization_provider,
                sentiment_provider=context.sentiment_provider,
                topic_modeling_provider=context.topic_modeling_provider,
            )
            logger.info(
                "media_processing.dispatch.text_task_enqueued",
                media_id=media_id,
                storage_provider=context.storage_provider,
            )
            return
        except Exception as exc:
            logger.error(
                "media_processing.dispatch.text_task_failed",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )
            _mark_media_failed(media_uuid, str(exc))
            return

    try:
        transcription_payload = TranscriptionTaskPayload(
            media_id=context.media_id,
            file_path=context.file_path,
            storage_provider=context.storage_provider,
            transcription_provider=context.transcription_provider,
            language=context.language,
            file_size_bytes=context.file_size_bytes,
            summarization_provider=context.summarization_provider,
            sentiment_provider=context.sentiment_provider,
            topic_modeling_provider=context.topic_modeling_provider,
        )
        process_transcription_task.delay(**transcription_payload.model_dump(mode="json"))
        logger.info(
            "media_processing.dispatch.transcription_enqueued",
            media_id=media_id,
            provider=context.transcription_provider,
            language=context.language,
        )
    except ValidationError as exc:
        logger.error(
            "media_processing.dispatch.invalid_transcription_payload",
            media_id=media_id,
            errors=exc.errors(),
        )
        _mark_media_failed(media_uuid, "invalid transcription payload")
        return
    except Exception as exc:
        logger.error(
            "media_processing.dispatch.transcription_enqueue_failed",
            media_id=media_id,
            error=str(exc),
            exc_info=True,
        )
        _mark_media_failed(media_uuid, "failed to enqueue transcription task")
        raise

    if (context.media_type or "").upper() == "VIDEO":
        try:
            video_payload = VideoTaskPayload(
                media_id=context.media_id,
                file_path=context.file_path,
                storage_provider=context.storage_provider,
                file_size_bytes=context.file_size_bytes,
            )
            process_video_task.delay(**video_payload.model_dump(mode="json"))
            logger.info(
                "media_processing.dispatch.video_enqueued",
                media_id=media_id,
                storage_provider=context.storage_provider,
            )
        except ValidationError as exc:
            logger.error(
                "media_processing.dispatch.invalid_video_payload",
                media_id=media_id,
                errors=exc.errors(),
            )
        except Exception as exc:
            logger.error(
                "media_processing.dispatch.video_enqueue_failed",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )

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
    from src.media_processing.transcription.bootstrap import (
        TranscriptionContainer,
    )
    from src.storage.infrastructure.dependencies import StorageServiceFactory

    event_bus = InMemoryEventBus()
    text_analysis_service = TextAnalysisService()
    event_bus.subscribe(
        TextContentReady,
        build_text_content_ready_handler(text_analysis_service),
    )

    # Create storage service based on provider
    storage_factory = StorageServiceFactory()
    storage_adapter = storage_factory.create_storage_service(payload.storage_provider)

    # Create container with dependencies, using shared metrics to prevent duplicates
    container = TranscriptionContainer(
        db=db,
        event_bus=event_bus,
    )

    # Create the service manually to pass the correct storage adapter with sync methods
    transcription_repo = container.transcription_repository()
    task_scheduler = container.task_scheduler()
    transcription_logger = container.transcription_logger()
    transcription_metrics = container.transcription_metrics()
    speech_recognizer_factory = container.speech_recognizer_factory()
    media_queries = container.media_queries()

    service = container.transcription_service(
        transcription_repo=transcription_repo,
        task_scheduler=task_scheduler,
        transcription_logger=transcription_logger,
        transcription_metrics=transcription_metrics,
        storage_service=storage_adapter,  # Use the adapter with sync methods
        speech_recognizer_factory=speech_recognizer_factory,
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
