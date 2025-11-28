from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.media_processing.application.dispatch_orchestrator import (
    DispatchAction,
    MediaDispatchOrchestrator,
)
from src.media_processing.application.job_runners import (
    run_transcription_job_sync,
    run_video_job_sync,
)
from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.shared.infrastructure.database import get_sync_session
from src.shared.events.integration_events import (
    TASK_MEDIA_TRANSCRIPTION,
    TASK_MEDIA_VIDEO_PROCESSING,
    TASK_TEXT_ANALYSIS_ANALYZE,
)

logger = structlog.get_logger(__name__)

_dispatch_orchestrator = MediaDispatchOrchestrator()


def _resolve_task_name(action: DispatchAction) -> str:
    if action.name == "text_document":
        return TASK_TEXT_ANALYSIS_ANALYZE
    if action.name == "transcription":
        return TASK_MEDIA_TRANSCRIPTION
    if action.name == "video":
        return TASK_MEDIA_VIDEO_PROCESSING
    raise KeyError(action.name)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_media_task(self, media_id: str) -> None:
    """Entry point that dispatches concrete processing tasks for a media item."""
    logger.info("media_processing.dispatch.started", media_id=media_id, correlation_id=media_id)

    try:
        media_uuid = UUID(str(media_id))
    except ValueError:
        logger.error("media_processing.dispatch.invalid_id", media_id=media_id)
        return

    try:
        actions = _dispatch_orchestrator.prepare_actions(media_uuid)
    except Exception as exc:
        logger.error("media_processing.dispatch.db_error", media_id=media_id, error=str(exc), exc_info=True)
        raise

    if not actions:
        return

    for action in actions:
        try:
            task_name = _resolve_task_name(action)
            # Use send_task for loose coupling (no direct imports of other modules)
            self.app.send_task(task_name, kwargs=action.payload)
            logger.info(
                "media_processing.dispatch.action_enqueued",
                media_id=media_id,
                action=action.name,
                target_task=task_name,
                correlation_id=media_id,
            )
        except ValidationError as exc:
            logger.error(
                f"media_processing.dispatch.{action.name}_payload_invalid",
                media_id=media_id,
                errors=exc.errors(),
            )
            if action.fatal:
                _dispatch_orchestrator.mark_failed(media_uuid, f"invalid {action.name} payload")
                return
        except Exception as exc:
            logger.error(
                f"media_processing.dispatch.{action.name}_enqueue_failed",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )
            if action.fatal:
                _dispatch_orchestrator.mark_failed(media_uuid, f"failed to enqueue {action.name} task")
                raise

    logger.info("media_processing.dispatch.completed", media_id=media_id, correlation_id=media_id)

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
    storage_provider: str,
    transcription_provider: str,
    language: str = "en",
    file_size_bytes: Optional[int] = None,
    summarization_provider: Optional[str] = None,
    sentiment_provider: Optional[str] = None,
    topic_modeling_provider: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **kwargs, 
) -> Optional[str]:
    correlation_id = correlation_id or media_id
    try:
        payload = TranscriptionTaskPayload.model_validate(
            {
                "media_id": media_id,
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
            correlation_id=correlation_id,
        )
        return None

    try:
        with get_sync_session() as db:
            transcription_text = run_transcription_job_sync(db, payload)
            
        # CHAINING: Automatically trigger text analysis if successful
        if transcription_text:
            logger.info("transcription.task.completed_triggering_analysis", media_id=media_id)
            
            analysis_payload = {
                "media_id": media_id,
                # We do not pass the huge text payload to avoid Broker limits.
                # The Text Analysis service should fetch it via Storage/DB using media_id.
                "language": language,
                "summarization_provider": summarization_provider,
                "sentiment_provider": sentiment_provider,
                "topic_modeling_provider": topic_modeling_provider,
                "provider": summarization_provider, 
                "correlation_id": correlation_id
            }
            
            self.app.send_task(TASK_TEXT_ANALYSIS_ANALYZE, kwargs=analysis_payload)
            
        return transcription_text

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
    max_retries=5
)
def process_video_task(
    self,
    media_id: str,
    # file_path removed
    storage_provider: str,
    file_size_bytes: Optional[int] = None,
    correlation_id: Optional[str] = None,
    **kwargs,
) -> Optional[Dict[str, Any]]:
    correlation_id = correlation_id or media_id
    try:
        payload = VideoTaskPayload.model_validate(
            {
                "media_id": media_id,
                "storage_provider": storage_provider,
                "file_size_bytes": file_size_bytes,
            }
        )
    except ValidationError as exc:
        logger.error(
            "video_processing.task_invalid_payload",
            media_id=media_id,
            errors=exc.errors(),
            correlation_id=correlation_id,
        )
        return None

    try:
        with get_sync_session() as db:
            return run_video_job_sync(db, payload)
    except Exception as e:
        logger.error(
            "video_processing.task_failed",
            extra={
                "media_id": media_id,
                "error": str(e),
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        return None
