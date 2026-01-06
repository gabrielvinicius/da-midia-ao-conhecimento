# src/media_management/bootstrap.py
"""Bootstrap media management module."""
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.api.dependencies import (
    get_media_service,
)
from src.media_management.application.event_handlers import MediaEventHandlers
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultStorageUploader,
    DefaultUploadMetadataMapper,
    StorageUploaderAdapter,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.media_processing.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.media_processing.application.event_handlers import MediaProcessingEventHandlers
from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.ports import TranscriptionQueryPort
from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.infrastructure.adapters.storage_download_adapter import (
    StorageDownloadAdapter,
)
from src.media_management.infrastructure.adapters.storage_downloader_adapter import (
    StorageDownloaderAdapter,
)
from src.media_management.infrastructure.adapters.file_validator_adapter import (
    MediaFileReferenceValidator,
)
from src.media_processing.infrastructure.adapters.transcription_cleanup_adapter import (
    TranscriptionCleanupAdapter,
)
from src.media_processing.infrastructure.dependencies.transcription_query_adapter import (
    TranscriptionQueryAdapter,
)
from src.media_processing.infrastructure.dependencies.providers import (
    get_audio_extractor,
    get_ocr_provider,
    get_speech_recognizer,
    get_text_extractor,
    get_thumbnail_generator,
)
from src.media_processing.infrastructure.logging import structured_transcription_logger
from src.media_processing.infrastructure.metrics import (
    prometheus_transcription_metrics,
    prometheus_video_processing_metrics,
)
from src.media_processing.infrastructure.repositories import transcription_repository
from src.media_processing.application.tasks import (
    CeleryTextTaskScheduler,
    CeleryTranscriptionTaskScheduler,
    CeleryVideoProcessingTaskScheduler,
)

StructuredTranscriptionLogger = (
    structured_transcription_logger.StructuredTranscriptionLogger
)
PrometheusTranscriptionMetrics = (
    prometheus_transcription_metrics.PrometheusTranscriptionMetrics
)
PrometheusVideoProcessingMetrics = (
    prometheus_video_processing_metrics.PrometheusVideoProcessingMetrics
)
TranscriptionRepository = transcription_repository.TranscriptionRepository
from src.shared.domain.events import (
    MediaUploaded,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.application.services.maintenance_service import (
    StorageMaintenanceService,
)
from src.storage.infrastructure.adapters.storage_maintenance_adapter import (
    StorageMaintenanceAdapter,
)


@dataclass
class MediaModule:
    """Public surface used by the media API and other modules."""

    media_service: MediaService

    transcription_service: TranscriptionService
    video_processing_service: VideoProcessingService
    # Read-side: consulta de transcrições (para outros contextos, ex.: text_analysis).
    transcription_queries: TranscriptionQueryPort


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
    storage_provider: str = "local",
) -> Tuple[MediaModule, MediaAdminContext]:
    """Compose the media module without relying on dependency-injector."""
    media_repository = MediaRepository(db=session)
    media_repo_adapter = MediaRepositoryAdapter(media_repository)
    media_read_service = MediaReadService(media_repository=media_repo_adapter)
    media_upload_validator = MediaUploadValidator(settings=media_settings)

    # Processing dependencies
    transcription_repository = TranscriptionRepository(db=session)
    transcription_queries = TranscriptionQueryAdapter(transcription_repository)
    transcription_metrics = PrometheusTranscriptionMetrics()
    transcription_storage_service = storage_service_factory.create_storage_service(
        storage_provider
    )

    storage_maintenance_service = StorageMaintenanceService(
        storage_port=StorageMaintenanceAdapter(storage_service_factory)
    )
    # Register validators
    storage_maintenance_service.register_validator(
        MediaFileReferenceValidator(media_repository)
    )

    # Text analysis cleanup adapter (needed for media deletion)
    from src.text_analysis.infrastructure.adapters.text_analysis_cleanup_adapter import (
        TextAnalysisCleanupAdapter,
    )
    from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
        SqlAlchemyAnalysisRepository,
    )
    analysis_repo = SqlAlchemyAnalysisRepository(session)

    media_service = MediaService(
        media_repository=media_repo_adapter,
        storage_uploader=DefaultStorageUploader(StorageUploaderAdapter(storage_service_factory)),
        metadata_mapper=DefaultUploadMetadataMapper(),
        metrics_service=metrics_service,
        upload_validator=media_upload_validator,
        media_read_service=media_read_service,
        event_bus=event_bus,
        storage_maintenance=storage_maintenance_service,
        transcription_cleanup=TranscriptionCleanupAdapter(transcription_repository),
        text_analysis_cleanup=TextAnalysisCleanupAdapter(analysis_repo),
        storage_downloader=StorageDownloaderAdapter(storage_service_factory),
    )
    transcription_service = TranscriptionService(
        transcription_repo=transcription_repository,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=transcription_metrics,
        storage_service=transcription_storage_service,
        speech_recognizer_factory=lambda provider: get_speech_recognizer(provider),
        media_queries=media_repository, # Duck typing
        event_bus=event_bus,
    )

    text_extraction_service = TextExtractionService(
        repository=transcription_repository,
        task_scheduler=CeleryTextTaskScheduler(),
        storage_service=transcription_storage_service,
        event_bus=event_bus,
        text_extractor=get_text_extractor(),
        ocr_provider=get_ocr_provider(),
    )

    video_processing_service = VideoProcessingService(
        video_audio_extractor=get_audio_extractor(),
        video_thumbnail_generator=get_thumbnail_generator(),
        video_processing_task_scheduler=CeleryVideoProcessingTaskScheduler(),
        storage_factory=StorageDownloadAdapter(storage_service_factory),
        event_bus=event_bus,
    )

    video_metrics = PrometheusVideoProcessingMetrics()

    # Instantiate and subscribe event handlers for media processing
    media_processing_event_handlers = MediaProcessingEventHandlers(
        transcription_service=transcription_service,
        text_extraction_service=text_extraction_service,
        video_processing_service=video_processing_service,
    )

    media_event_handlers = MediaEventHandlers(media_service)

    if event_bus:
        event_bus.subscribe(
            MediaUploaded,
            media_processing_event_handlers.handle_media_uploaded,
        )
        # TextContentReady handled in text_analysis module
        event_bus.subscribe(
            TranscriptionCompleted,
            media_event_handlers.handle_transcription_completed,
        )
        event_bus.subscribe(
            TranscriptionFailed,
            media_event_handlers.handle_transcription_failed,
        )

    module = MediaModule(
        media_service=media_service,
        transcription_service=transcription_service,
        video_processing_service=video_processing_service,
        transcription_queries=transcription_queries,
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
        )
    )


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "bind_media_module",
    "build_media_components",
]
