"""Shared executors for Celery processing tasks."""
from __future__ import annotations

import asyncio
from typing import Optional
from uuid import UUID

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.shared.domain.enums import MediaStatus
from src.media_management.infrastructure.media_repository_sync import (
    MediaRepositorySync,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.infrastructure.transcription.dependencies import (
    create_speech_recognition_service,
)
from src.media_processing.infrastructure.transcription.logging import (
    StructuredTranscriptionLogger,
)
from src.media_processing.infrastructure.transcription.metrics import (
    PrometheusTranscriptionMetrics,
)
from src.media_processing.infrastructure.transcription.transcription_repository import (
    TranscriptionRepository,
)
from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.infrastructure.video_processing.metrics import (
    PrometheusVideoProcessingMetrics,
)
from src.media_processing.infrastructure.video_processing.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.media_processing.infrastructure.video_processing.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.domain_events import (
    MediaProcessingStarted,
    MediaProcessingCompleted,
    MediaProcessingFailed
)
from src.media_management.application.events import MediaStatusHandler


class _NoopTranscriptionTaskScheduler:
    async def schedule_transcription_task(self, *args, **kwargs):  # pragma: no cover - Celery path only
        return {"task_id": None}


class _NoopVideoTaskScheduler:
    async def schedule_process_video_task(self, *args, **kwargs):  # pragma: no cover - Celery path only
        return {"task_id": None}


def _publish_sync(event_bus, event):
    """Bridge async event publication to sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(event_bus.publish(event))


def run_transcription_job_sync(db, payload: TranscriptionTaskPayload) -> Optional[str]:
    """Execute the transcription pipeline in-process for Celery."""
    # media_queries = MediaQueriesSync(media_repository=media_repo) <- Removed
    # Passing repository directly as it satisfies the interface required by TranscriptionService (get_by_id)
    media_queries = media_repo
    storage_factory = StorageServiceFactory()

    # Wire up handlers for In-Process Domain Event Handling
    status_handler = MediaStatusHandler(media_repo)
    event_bus.subscribe(MediaProcessingStarted, status_handler.on_processing_started)
    event_bus.subscribe(MediaProcessingCompleted, status_handler.on_processing_completed)
    event_bus.subscribe(MediaProcessingFailed, status_handler.on_processing_failed)

    from src.media_processing.application.services.text_analysis_dispatcher import TextAnalysisDispatcher

    dispatcher = TextAnalysisDispatcher(event_bus=event_bus)
    
    # Note: MediaProcessingServiceSingleton wiring skipped for simplification as per refactor

    media = media_repo.get_by_id(payload.media_id)
    if media is None:
        raise FileNotFoundError(f"Media '{payload.media_id}' not found")

    storage_provider = payload.storage_provider or getattr(media, "storage_provider", None) or "local"
    storage_adapter = storage_factory.create_storage_service(storage_provider)
    file_path = getattr(media, "original_file_path", None)
    if not file_path:
        raise FileNotFoundError(f"Media '{payload.media_id}' missing original file path")

    service = TranscriptionService(
        transcription_repo=transcription_repo,
        task_scheduler=_NoopTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=PrometheusTranscriptionMetrics(),
        storage_service=storage_adapter,
        speech_recognizer_factory=create_speech_recognition_service,
        media_queries=media_queries,
        event_bus=event_bus,
        dispatcher=dispatcher,
    )

    # Publish STARTED event via Bus instead of direct Repo update
    _publish_sync(event_bus, MediaProcessingStarted(media_id=str(payload.media_id)))

    try:
        result = service.process_transcription_job_sync(
            media_id=payload.media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=payload.transcription_provider,
            language=payload.language,
            summarization_provider=payload.summarization_provider,
            sentiment_provider=payload.sentiment_provider,
            topic_modeling_provider=payload.topic_modeling_provider,
        )
        
        # Publish COMPLETED event
        # Note: service.process_transcription_job_sync might return successfully even if internal error handled?
        # Assuming exception raised if failed.
        _publish_sync(event_bus, MediaProcessingCompleted(media_id=str(payload.media_id)))
        
        return result
    except Exception as exc:
        # Publish FAILED event
        _publish_sync(event_bus, MediaProcessingFailed(
            media_id=str(payload.media_id), 
            error_message=str(exc)
        ))
        raise


def run_video_job_sync(db, payload: VideoTaskPayload) -> Optional[dict]:
    """Execute the video pipeline in-process for Celery."""
    # Each worker process builds its own event bus instance
    from src.shared.event_bus_factory import get_event_bus
    event_bus = get_event_bus()
    
    storage_factory = StorageServiceFactory()
    media_repo = MediaRepositorySync(db=db)
    
    # Wire up handlers
    status_handler = MediaStatusHandler(media_repo)
    event_bus.subscribe(MediaProcessingStarted, status_handler.on_processing_started)
    event_bus.subscribe(MediaProcessingCompleted, status_handler.on_processing_completed)
    event_bus.subscribe(MediaProcessingFailed, status_handler.on_processing_failed)

    media = media_repo.get_by_id(payload.media_id)
    if media is None:
        raise FileNotFoundError(f"Media '{payload.media_id}' not found")
    file_path = getattr(media, "original_file_path", None)
    if not file_path:
        raise FileNotFoundError(f"Media '{payload.media_id}' missing original file path")

    service = VideoProcessingService(
        video_audio_extractor=FFmpegVideoAudioExtractor(),
        video_thumbnail_generator=FFmpegVideoThumbnailGenerator(),
        video_processing_task_scheduler=_NoopVideoTaskScheduler(),
        storage_factory=storage_factory,
        video_processing_metrics=PrometheusVideoProcessingMetrics(),
    )

    # Publish STARTED event
    _publish_sync(event_bus, MediaProcessingStarted(media_id=str(payload.media_id)))

    try:
        result = service.process_video_job_sync(
            media_id=payload.media_id,
            file_path=file_path,
            storage_provider=payload.storage_provider,
            file_size_bytes=payload.file_size_bytes,
        )
        # Publish COMPLETED event
        _publish_sync(event_bus, MediaProcessingCompleted(media_id=str(payload.media_id)))
        return result
    except Exception as exc:
        # Publish FAILED event
        _publish_sync(event_bus, MediaProcessingFailed(
            media_id=str(payload.media_id), 
            error_message=str(exc)
        ))
        raise


__all__ = ["run_transcription_job_sync", "run_video_job_sync"]
