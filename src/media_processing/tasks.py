from typing import Any, Dict, Optional

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.shared.event_bus import InMemoryEventBus
from src.shared.events.domain_events import TextContentReady
from src.shared.infrastructure.database import get_sync_db
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.text_analysis.application.event_handlers import build_text_content_ready_handler
from src.text_analysis.application.services import TextAnalysisService

logger = structlog.get_logger(__name__)

@shared_task
def placeholder_media_processing_task():
    """Placeholder task for media processing."""
    pass

# Backward compatibility: some modules still import process_media_task explicitly
process_media_task = placeholder_media_processing_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_transcription_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    transcription_provider: str,
    language: str = "en",
    file_size_bytes: Optional[int] = None,
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
        from src.shared.infrastructure.database import get_sync_session
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
        from src.shared.infrastructure.database import get_sync_session
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