"""Shared executors for Celery processing tasks."""
from __future__ import annotations

from typing import Optional

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.transcription.infrastructure.dependencies import (
    create_speech_recognition_service,
)
from src.media_processing.transcription.infrastructure.logging import (
    StructuredTranscriptionLogger,
)
from src.media_processing.transcription.infrastructure.metrics import (
    PrometheusTranscriptionMetrics,
)
from src.media_processing.transcription.infrastructure.transcription_repository import (
    TranscriptionRepository,
)
from src.media_processing.video_processing.application.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.video_processing.infrastructure.metrics import (
    PrometheusVideoProcessingMetrics,
)
from src.media_processing.video_processing.infrastructure.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.media_processing.video_processing.infrastructure.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.shared.event_bus import InMemoryEventBus
from src.shared.events.domain_events import TextContentReady
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.text_analysis.application.event_handlers import build_text_content_ready_handler
from src.text_analysis.application.services import TextAnalysisService


class _NoopTranscriptionTaskScheduler:
    async def schedule_transcription_task(self, *args, **kwargs):  # pragma: no cover - Celery path only
        return {"task_id": None}


class _NoopVideoTaskScheduler:
    async def schedule_process_video_task(self, *args, **kwargs):  # pragma: no cover - Celery path only
        return {"task_id": None}


def run_transcription_job_sync(db, payload: TranscriptionTaskPayload) -> Optional[str]:
    """Execute the transcription pipeline in-process for Celery."""
    from src.media_management.application.queries.media_queries import MediaQueries
    from src.media_management.infrastructure.media_repository import MediaRepository

    storage_factory = StorageServiceFactory()
    storage_adapter = storage_factory.create_storage_service(payload.storage_provider)

    transcription_repo = TranscriptionRepository(db)
    media_repo = MediaRepository(db=db)
    media_queries = MediaQueries(media_repository=media_repo)

    event_bus = InMemoryEventBus()
    text_analysis_service = TextAnalysisService()
    event_bus.subscribe(
        TextContentReady,
        build_text_content_ready_handler(text_analysis_service),
    )

    service = TranscriptionService(
        transcription_repo=transcription_repo,
        task_scheduler=_NoopTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=PrometheusTranscriptionMetrics(),
        storage_service=storage_adapter,
        speech_recognizer_factory=create_speech_recognition_service,
        db_session=db,
        media_queries=media_queries,
        event_bus=event_bus,
    )

    return service.process_transcription_job_sync(
        media_id=payload.media_id,
        file_path=payload.file_path,
        storage_provider=payload.storage_provider,
        transcription_provider=payload.transcription_provider,
        language=payload.language,
        summarization_provider=payload.summarization_provider,
        sentiment_provider=payload.sentiment_provider,
        topic_modeling_provider=payload.topic_modeling_provider,
    )


def run_video_job_sync(db, payload: VideoTaskPayload) -> Optional[dict]:
    """Execute the video pipeline in-process for Celery."""
    storage_factory = StorageServiceFactory()

    service = VideoProcessingService(
        video_audio_extractor=FFmpegVideoAudioExtractor(),
        video_thumbnail_generator=FFmpegVideoThumbnailGenerator(),
        video_processing_task_scheduler=_NoopVideoTaskScheduler(),
        storage_factory=storage_factory,
        video_processing_metrics=PrometheusVideoProcessingMetrics(),
    )

    result = service.process_video_job_sync(
        media_id=payload.media_id,
        file_path=payload.file_path,
        storage_provider=payload.storage_provider,
        file_size_bytes=payload.file_size_bytes,
    )
    return result


__all__ = ["run_transcription_job_sync", "run_video_job_sync"]
