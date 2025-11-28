"""Shared executors for Celery processing tasks."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.media_management.domain.enums import MediaStatus
from src.media_management.infrastructure.media_repository_sync import (
    MediaRepositorySync,
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
from src.storage.infrastructure.dependencies import StorageServiceFactory


class _NoopTranscriptionTaskScheduler:
    async def schedule_transcription_task(self, *args, **kwargs):  # pragma: no cover - Celery path only
        return {"task_id": None}


class _NoopVideoTaskScheduler:
    async def schedule_process_video_task(self, *args, **kwargs):  # pragma: no cover - Celery path only
        return {"task_id": None}


def _record_nonfatal_error(
    repository: "MediaRepositorySync",
    media_id: UUID,
    message: str,
) -> None:
    try:
        aggregate = repository.get_by_id(media_id)
    except Exception:
        return
    if aggregate is None:
        return
    repository.update_status(media_id, aggregate.status, error_message=message)


def run_transcription_job_sync(db, payload: TranscriptionTaskPayload) -> Optional[str]:
    """Execute the transcription pipeline in-process for Celery."""
    from src.media_management.application.queries.media_queries_sync import (
        MediaQueriesSync,
    )

    # Each worker process builds its own event bus instance
    from src.shared.event_bus_factory import get_event_bus
    event_bus = get_event_bus()

    transcription_repo = TranscriptionRepository(db)
    media_repo = MediaRepositorySync(db=db)
    media_queries = MediaQueriesSync(media_repository=media_repo)
    storage_factory = StorageServiceFactory()

    from src.media_processing.application.text_analysis_dispatcher import TextAnalysisDispatcher

    dispatcher = TextAnalysisDispatcher(event_bus=event_bus)

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
        db_session=db,
        media_queries=media_queries,
        event_bus=event_bus,
        dispatcher=dispatcher,
    )

    # Ensure the UI receives progress notifications for each stage.
    media_repo.update_status(
        payload.media_id,
        MediaStatus.PROCESSING,
        error_message=None,
        force_notify=True,
    )

    try:
        return service.process_transcription_job_sync(
            media_id=payload.media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=payload.transcription_provider,
            language=payload.language,
            summarization_provider=payload.summarization_provider,
            sentiment_provider=payload.sentiment_provider,
            topic_modeling_provider=payload.topic_modeling_provider,
        )
    except Exception as exc:
        try:
            media_repo.update_status(
                payload.media_id,
                MediaStatus.FAILED,
                error_message=str(exc),
            )
        except ValueError:
            _record_nonfatal_error(
                media_repo,
                payload.media_id,
                f"transcription failed: {exc}",
            )
        raise


def run_video_job_sync(db, payload: VideoTaskPayload) -> Optional[dict]:
    """Execute the video pipeline in-process for Celery."""
    storage_factory = StorageServiceFactory()
    media_repo = MediaRepositorySync(db=db)

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

    media_repo.update_status(
        payload.media_id,
        MediaStatus.PROCESSING,
        error_message=None,
        force_notify=True,
    )

    try:
        return service.process_video_job_sync(
            media_id=payload.media_id,
            file_path=file_path,
            storage_provider=payload.storage_provider,
            file_size_bytes=payload.file_size_bytes,
        )
    except Exception as exc:
        _record_nonfatal_error(
            media_repo,
            payload.media_id,
            f"video processing failed: {exc}",
        )
        raise


__all__ = ["run_transcription_job_sync", "run_video_job_sync"]
