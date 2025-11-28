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

logger = structlog.get_logger(__name__)

_dispatch_orchestrator = MediaDispatchOrchestrator()


def _resolve_task_executor(action: DispatchAction):
    if action.name == "text_document":
        from src.text_analysis.tasks import process_text_document_task

        return process_text_document_task
    if action.name == "transcription":
        return process_transcription_task
    if action.name == "video":
        return process_video_task
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
        task = None
        try:
            task = _resolve_task_executor(action)
            task.delay(**action.payload)
            logger.info(
                "media_processing.dispatch.action_enqueued",
                media_id=media_id,
                action=action.name,
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
    correlation_id: Optional[str] = None,
) -> Optional[str]:
    correlation_id = correlation_id or media_id
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
            correlation_id=correlation_id,
        )
        return None

    try:
        with get_sync_session() as db:
            return run_transcription_job_sync(db, payload)
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


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_video_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    file_size_bytes: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    correlation_id = correlation_id or media_id
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
