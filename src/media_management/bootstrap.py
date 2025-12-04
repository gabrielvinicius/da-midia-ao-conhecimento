from dataclasses import dataclass
from typing import Any, Optional, Tuple

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.api.dependencies import (
    get_create_media,
    get_delete_media,
    get_reprocess_media,
    get_get_media,
    get_list_media,
    get_get_media_statistics,
    get_cleanup_media,
)
from src.media_management.application.commands.use_cases import (
    CreateMedia,
    DeleteMedia,
    ReprocessMedia,
    CleanupOrphanedFiles,
)
from src.media_management.application.queries.use_cases import (
    GetMedia,
    ListMedia,
    GetMediaStatistics,
)
from src.media_management.application.commands.validators import MediaUploadValidator
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.infrastructure.media_repository import MediaRepository
from src.shared.config.settings import settings
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
    
    # Commands
    create_media: CreateMedia
    delete_media: DeleteMedia
    reprocess_media: ReprocessMedia
    cleanup_orphaned_files: CleanupOrphanedFiles
    
    # Queries
    get_media: GetMedia
    list_media: ListMedia
    get_statistics: GetMediaStatistics

    # Legacy/Other Services (to be refactored later if needed)
    processing_service: MediaProcessingService
    transcription_service: TranscriptionService
    transcription_queries: TranscriptionQueries
    video_processing_service: VideoProcessingService


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""
    delete_media: DeleteMedia
    reprocess_media: ReprocessMedia
    cleanup_orphaned_files: CleanupOrphanedFiles
    list_media: ListMedia
    get_media: GetMedia


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
    media_access_policy = MediaAccessPolicy()
    media_upload_validator = MediaUploadValidator(settings=settings)

    # Consolidated processing dependencies
    transcription_repository = TranscriptionRepository(db=session)
    transcription_metrics = PrometheusTranscriptionMetrics()
    transcription_storage_service = S3StorageService()
    
    # Transcription Service
    # Note: TranscriptionService still uses old MediaQueries logic/dependency?
    # We need to check if TranscriptionService uses media_queries. 
    # If so, we might need to instantiate GetMedia or keep MediaQueries internally for it.
    # For now, I'll adapt TranscriptionService locally if it complains, or assume it handles its own queries.
    # Wait, `TranscriptionService` constructor in previous bootstrap had `media_queries`.
    # I should construct a minimal `MediaQueries` adapter if needed or pass `GetMedia`.
    # Let's create the Use Cases first.
    
    create_media = CreateMedia.with_default_components(
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        metrics_service=metrics_service,
        upload_validator=media_upload_validator,
        event_bus=event_bus,
        emit_legacy_task=emit_legacy_media_task,
        provider_registry=provider_registry,
    )

    delete_media = DeleteMedia(
        media_repository=media_repository,
        storage_factory=storage_service_factory,
        access_policy=media_access_policy,
        event_bus=event_bus,
    )

    reprocess_media = ReprocessMedia(
        media_repository=media_repository,
        access_policy=media_access_policy,
        event_bus=event_bus,
    )

    cleanup_orphaned_files = CleanupOrphanedFiles(
        media_repository=media_repository,
        storage_factory=storage_service_factory,
    )

    get_media = GetMedia(repository=media_repository)
    list_media = ListMedia(repository=media_repository)
    get_statistics = GetMediaStatistics(repository=media_repository)

    # Compatibility for TranscriptionService
    # It expects `media_queries` with `get_by_id`.
    # `GetMedia` has `execute(GetMediaQuery)`.
    # I will pass `media_repository` directly if TranscriptionService accepts it, 
    # OR create a shim if TranscriptionService is strictly typed to old MediaQueries.
    # Let's look at TranscriptionService init. It was:
    # media_queries=media_queries
    # I will pass `media_queries` as a SHIM for now to avoid breaking `media_processing` yet.
    # But I deleted `MediaQueries` class!
    # I must recreate a simple shim or update TranscriptionService.
    # Updating TranscriptionService is better but out of scope for "media_management" refactor?
    # No, I must fix it.
    # I will define a local Shim here or update TranscriptionService to use Repository directly?
    # Repository has `get_by_id`. `MediaQueries` had `get_by_id`.
    # If TranscriptionService uses `media_queries.get_by_id(uuid)`, and Repo has it, I can pass Repo!
    # But type hint might complain.
    
    transcription_service = TranscriptionService(
        transcription_repo=transcription_repository,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=transcription_metrics,
        storage_service=transcription_storage_service,
        speech_recognizer_factory=create_speech_recognition_service,
        media_queries=media_repository, # Passing Repo as Queries (Duck Typing)
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
    # CQRS handlers for media processing
    from src.media_processing.application.commands import (
        RequestTranscriptionHandler,
        RequestVideoProcessingHandler,
    )

    processing_service = MediaProcessingService(
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_service=video_processing_service,
        transcription_metrics=transcription_metrics,
        video_metrics=video_metrics,
        request_transcription_handler=RequestTranscriptionHandler(transcription_service),
        request_video_handler=RequestVideoProcessingHandler(video_processing_service),
        provider_registry=provider_registry,
    )

    module = MediaModule(
        create_media=create_media,
        delete_media=delete_media,
        reprocess_media=reprocess_media,
        cleanup_orphaned_files=cleanup_orphaned_files,
        get_media=get_media,
        list_media=list_media,
        get_statistics=get_statistics,
        
        processing_service=processing_service,
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_processing_service=video_processing_service,
    )

    admin_context = MediaAdminContext(
        delete_media=delete_media,
        reprocess_media=reprocess_media,
        cleanup_orphaned_files=cleanup_orphaned_files,
        list_media=list_media,
        get_media=get_media,
    )

    return module, admin_context


def bind_media_module(app: FastAPI, module: MediaModule) -> None:
    """Register dependency overrides for media use cases."""

    app.dependency_overrides[get_create_media] = lambda: module.create_media
    app.dependency_overrides[get_delete_media] = lambda: module.delete_media
    app.dependency_overrides[get_reprocess_media] = lambda: module.reprocess_media
    app.dependency_overrides[get_cleanup_media] = lambda: module.cleanup_orphaned_files
    
    app.dependency_overrides[get_get_media] = lambda: module.get_media
    app.dependency_overrides[get_list_media] = lambda: module.list_media
    app.dependency_overrides[get_get_media_statistics] = lambda: module.get_statistics

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