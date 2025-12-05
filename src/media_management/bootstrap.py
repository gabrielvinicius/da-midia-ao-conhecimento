# src/media_management/bootstrap.py
"""Bootstrap media management module."""
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.api.dependencies import (
    get_media_service,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.commands.validators import MediaUploadValidator
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.shared.config.settings import settings
from src.media_processing.application.media_processing_service import MediaProcessingService
from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.transcription.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.providers.domain.interfaces import IProviderRegistry
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
    
    media_service: MediaService
    
    # Legacy/Other Services (to be refactored later if needed)
    processing_service: MediaProcessingService
    transcription_service: TranscriptionService
    video_processing_service: VideoProcessingService


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""
    media_service: MediaService
    
    # For backward compatibility if accessing properties directly
    @property
    def queries(self):
        return self.media_service


def build_media_components(
    session: AsyncSession,
    *,
    storage_service_factory: Any,
    metrics_service: Any,
    event_bus: Optional[SupportsEventBus] = None,
    emit_legacy_media_task: bool = True,
    provider_registry: Optional[IProviderRegistry] = None,
) -> Tuple[MediaModule, MediaAdminContext]:
    """Compose the media module without relying on dependency-injector."""
    media_repository = MediaRepository(db=session)
    media_upload_validator = MediaUploadValidator(settings=settings)

    # Consolidated processing dependencies
    transcription_repository = TranscriptionRepository(db=session)
    transcription_metrics = PrometheusTranscriptionMetrics()
    transcription_storage_service = S3StorageService()
    
    media_service = MediaService(
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        metrics_service=metrics_service,
        upload_validator=media_upload_validator,
        event_bus=event_bus,
        emit_legacy_task=emit_legacy_media_task,
        provider_registry=provider_registry,
    )

    transcription_service = TranscriptionService(
        transcription_repo=transcription_repository,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=transcription_metrics,
        storage_service=transcription_storage_service,
        speech_recognizer_factory=create_speech_recognition_service,
        media_queries=media_repository, # Duck typing
        event_bus=event_bus,
    )

    video_processing_service = VideoProcessingService(
        video_audio_extractor=FFmpegVideoAudioExtractor(),
        video_thumbnail_generator=FFmpegVideoThumbnailGenerator(),
        video_processing_task_scheduler=CeleryVideoProcessingTaskScheduler(),
        storage_factory=storage_service_factory,
    )

    video_metrics = PrometheusVideoProcessingMetrics()

    processing_service = MediaProcessingService(
        transcription_service=transcription_service,
        video_service=video_processing_service,
        transcription_metrics=transcription_metrics,
        video_metrics=video_metrics,
        provider_registry=provider_registry,
    )

    module = MediaModule(
        media_service=media_service,
        processing_service=processing_service,
        transcription_service=transcription_service,
        video_processing_service=video_processing_service,
    )

    admin_context = MediaAdminContext(
        media_service=media_service,
    )

    return module, admin_context


def bind_media_module(app: FastAPI, module: MediaModule) -> None:
    """Register dependency overrides for media use cases."""

    app.dependency_overrides[get_media_service] = lambda: module.media_service

    app.dependency_overrides[get_transcription_dependencies] = (
        lambda: TranscriptionDependencies(
            service=module.transcription_service,
            queries=module.transcription_service, # Duck typing
        )
    )


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "bind_media_module",
    "build_media_components",
]