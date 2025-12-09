import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from celery import shared_task
from asgiref.sync import async_to_sync

from src.shared.infrastructure.db import AsyncSessionLocal
from src.shared.infrastructure.event_bus_factory import get_event_bus
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.shared.events.integration_events import (
    TASK_MEDIA_TRANSCRIPTION,
    TASK_MEDIA_VIDEO_PROCESSING,
)
from src.media_processing.infrastructure.transcription.transcription_repository import TranscriptionRepository
from src.media_processing.infrastructure.transcription.dependencies import create_speech_recognition_service
from src.media_processing.infrastructure.transcription.metrics import PrometheusTranscriptionMetrics
from src.media_processing.infrastructure.transcription.logging import StructuredTranscriptionLogger
from src.media_processing.application.services.transcription_service import TranscriptionService
from src.media_processing.infrastructure.transcription.task_scheduler import CeleryTranscriptionTaskScheduler

logger = structlog.get_logger(__name__)

def bootstrap_transcription_service(session, event_bus) -> TranscriptionService:
    repo = TranscriptionRepository(session)
    metrics = PrometheusTranscriptionMetrics()
    transcription_logger = StructuredTranscriptionLogger()
    storage = S3StorageService()
    scheduler = CeleryTranscriptionTaskScheduler()
    
    return TranscriptionService(
        transcription_repo=repo,
        task_scheduler=scheduler,
        transcription_logger=transcription_logger,
        transcription_metrics=metrics,
        storage_service=storage,
        speech_recognizer_factory=create_speech_recognition_service,
        media_queries=None, 
        event_bus=event_bus
    )

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
    **kwargs, 
) -> Optional[Dict[str, Any]]:
    correlation_id = correlation_id or media_id
    logger.info("transcription.task_started", media_id=media_id, transcription_id=transcription_id)

    async def _run():
        async with AsyncSessionLocal() as session:
            event_bus = get_event_bus()
            service = bootstrap_transcription_service(session, event_bus)
            
            return await service.execute_transcription(
                transcription_id=UUID(transcription_id),
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
                summarization_provider=summarization_provider,
                sentiment_provider=sentiment_provider,
                topic_modeling_provider=topic_modeling_provider
            )

    try:
        result = async_to_sync(_run)()
        return result
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

@shared_task(name=TASK_MEDIA_VIDEO_PROCESSING)
def process_video_task(
    media_id: str,
    storage_provider: str,
    file_size_bytes: Optional[int] = None,
    correlation_id: Optional[str] = None,
    **kwargs,
):
    logger.warning("Video processing task not fully refactored yet.")
    return None
