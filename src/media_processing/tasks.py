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
        with get_sync_session() as db:
            return run_transcription_job_sync(db, payload)
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
        with get_sync_session() as db:
            return run_video_job_sync(db, payload)
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
