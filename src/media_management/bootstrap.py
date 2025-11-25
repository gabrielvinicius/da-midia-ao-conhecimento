from dataclasses import dataclass
from typing import Any, Optional, Tuple

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.api.dependencies import (
    MediaDependencies,
    get_media_dependencies,
)
from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.application.facade import MediaOrchestrator
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import MediaService
from src.media_management.application.validators import MediaUploadValidator
from src.media_management.config.settings import MediaSettings
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_processing.application.services import MediaProcessingService
from src.media_processing.transcription.application.queries import (
    TranscriptionQueries,
)
from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.transcription.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.media_processing.transcription.infrastructure.logging import (
    StructuredTranscriptionLogger,
)
from src.media_processing.transcription.infrastructure.dependencies import (
    create_speech_recognition_service,
)
from src.media_processing.transcription.infrastructure.metrics import (
    PrometheusTranscriptionMetrics,
)
from src.media_processing.transcription.infrastructure.task_scheduler import (
    CeleryTranscriptionTaskScheduler,
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
from src.media_processing.video_processing.infrastructure.task_scheduler import (
    CeleryVideoProcessingTaskScheduler,
)
from src.media_processing.video_processing.infrastructure.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.media_processing.video_processing.infrastructure.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.shared.events.bus import SupportsEventBus
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService


@dataclass
class MediaModule:
    """Public surface used by the media API and other modules."""

    queries: MediaQueries
    service: MediaService
    orchestrator: MediaOrchestrator
    processing_service: MediaProcessingService
    transcription_service: TranscriptionService
    transcription_queries: TranscriptionQueries
    video_processing_service: VideoProcessingService


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""

    queries: MediaQueries
    orchestrator: MediaOrchestrator


def build_media_components(
    session: AsyncSession,
    *,
    storage_service_factory: Any,
    metrics_service: Any,
    event_bus: Optional[SupportsEventBus] = None,
    emit_legacy_media_task: bool = True,
) -> Tuple[MediaModule, MediaAdminContext]:
    """Compose the media module without relying on dependency-injector."""
    media_repository = MediaRepository(db=session)
    media_queries = MediaQueries(media_repository=media_repository)
    media_logger = StructuredMediaLogger()
    media_metrics = PrometheusMediaMetrics()
    media_access_policy = MediaAccessPolicy()

    # Consolidated processing dependencies
    transcription_repository = TranscriptionRepository(db=session)
    transcription_metrics = PrometheusTranscriptionMetrics()
    transcription_storage_service = S3StorageService()
    transcription_service = TranscriptionService(
        transcription_repo=transcription_repository,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=transcription_metrics,
        storage_service=transcription_storage_service,
        speech_recognizer_factory=create_speech_recognition_service,
        db_session=session,
        media_queries=media_queries,
        event_bus=event_bus,
    )
    transcription_queries = TranscriptionQueries(transcription_repository=transcription_repository)

    video_processing_service = VideoProcessingService(
        video_audio_extractor=FFmpegVideoAudioExtractor(),
        video_thumbnail_generator=FFmpegVideoThumbnailGenerator(),
        video_processing_task_scheduler=CeleryVideoProcessingTaskScheduler(),
        storage_factory=storage_service_factory,
    )

    video_metrics = PrometheusVideoProcessingMetrics()
    processing_service = MediaProcessingService(
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_service=video_processing_service,
        transcription_metrics=transcription_metrics,
        video_metrics=video_metrics,
    )

    create_media_handler = CreateMediaCommandHandler.with_default_components(
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        metrics_service=metrics_service,
        event_bus=event_bus,
        emit_legacy_task=emit_legacy_media_task,
    )

    delete_media_handler = DeleteMediaCommandHandler(
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics,
        storage_factory=storage_service_factory,
    )

    reprocess_media_handler = ReprocessMediaCommandHandler(
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics,
    )

    media_upload_validator = MediaUploadValidator(settings=MediaSettings())

    media_service = MediaService(
        media_queries=media_queries,
        create_media_handler=create_media_handler,
        delete_media_handler=delete_media_handler,
        reprocess_media_handler=reprocess_media_handler,
        upload_validator=media_upload_validator,
        access_policy=media_access_policy,
    )

    orchestrator = MediaOrchestrator(
        queries=media_queries,
        media_service=media_service,
        event_bus=event_bus,
        storage_factory=storage_service_factory,
    )

    module = MediaModule(
        queries=media_queries,
        service=media_service,
        orchestrator=orchestrator,
        processing_service=processing_service,
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_processing_service=video_processing_service,
    )

    admin_context = MediaAdminContext(
        queries=media_queries,
        orchestrator=orchestrator,
    )

    return module, admin_context


def bind_media_module(app: FastAPI, module: MediaModule) -> None:
    """Register dependency overrides for media and transcription services."""

    app.dependency_overrides[get_media_dependencies] = lambda: MediaDependencies(
        queries=module.queries,
        service=module.service,
        orchestrator=module.orchestrator,
    )

    app.dependency_overrides[get_transcription_dependencies] = (
        lambda: TranscriptionDependencies(
            service=module.transcription_service,
            queries=module.transcription_queries,
        )
    )


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "bind_media_module",
    "build_media_components",
]
