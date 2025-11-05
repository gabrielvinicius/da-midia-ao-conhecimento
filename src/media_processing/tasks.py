import asyncio
from typing import Any, Dict, Optional

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.shared.infrastructure.database import get_db
from src.storage.infrastructure.dependencies import StorageServiceFactory

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
        return asyncio.run(
            _execute_transcription_job(
                payload=payload,
            )
        )
    except Exception as e:
        logger.error(
            "transcription.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None


async def _execute_transcription_job(
    *,
    payload: TranscriptionTaskPayload,
) -> Optional[str]:
    # Lazy imports to avoid circular dependency during module import
    from src.media_processing.transcription.bootstrap import (
        TranscriptionContainer,
    )

    async for db in get_db():
        container = TranscriptionContainer(db=db)
        service = container.transcription_service()
        return await service.process_transcription_job(
            media_id=payload.media_id,
            file_path=payload.file_path,
            storage_provider=payload.storage_provider,
            transcription_provider=payload.transcription_provider,
            language=payload.language,
        )


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
        return asyncio.run(
            _execute_video_processing_job(
                payload=payload,
            )
        )
    except Exception as e:
        logger.error(
            "video_processing.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _execute_video_processing_job(
    *,
    payload: VideoTaskPayload,
) -> Optional[Dict[str, Any]]:
    from src.media_processing.video_processing.bootstrap import (
        VideoProcessingContainer,
    )

    async for db in get_db():
        storage_factory = StorageServiceFactory()
        container = VideoProcessingContainer(
            db=db,
            storage_factory=storage_factory,
            storage_provider=payload.storage_provider,
        )
        service = container.video_processing_service()
        return await service.process_video_job(
            media_id=payload.media_id,
            file_path=payload.file_path,
            storage_provider=payload.storage_provider,
            file_size_bytes=payload.file_size_bytes,
        )
