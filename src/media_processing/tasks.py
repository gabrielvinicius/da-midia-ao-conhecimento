from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from celery import shared_task
from pydantic import ValidationError

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
                # We pass ID reference only. Text is fetched from DB by TextAnalysisService.
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