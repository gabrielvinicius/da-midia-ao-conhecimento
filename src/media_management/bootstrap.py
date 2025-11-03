from dataclasses import dataclass
from typing import Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.application.facade import MediaManagementFacade
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)
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
from src.media_processing.video_processing.application.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.transcription.infrastructure.logging import (
    StructuredTranscriptionLogger,
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
from src.media_processing.video_processing.infrastructure.task_scheduler import (
    CeleryVideoProcessingTaskScheduler,
)
from src.media_processing.video_processing.infrastructure.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.media_processing.video_processing.infrastructure.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.media_processing.video_processing.infrastructure.metrics import (
    PrometheusVideoProcessingMetrics,
)
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.shared.events.bus import SupportsEventBus
from src.shared.events.domain_events import MediaUploaded, TextContentReady


@dataclass
class MediaModule:
    """Public surface used by the media API and other modules."""

    queries: MediaQueries
    upload_service: MediaUploadService
    lifecycle_service: MediaLifecycleService
    query_service: MediaQueryService
    facade: MediaManagementFacade
    access_policy: MediaAccessPolicy
    processing_service: MediaProcessingService
    transcription_service: TranscriptionService
    transcription_queries: TranscriptionQueries
    video_processing_service: VideoProcessingService


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""

    queries: MediaQueries
    facade: MediaManagementFacade


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
    transcription_service = TranscriptionService(
        transcription_repo=transcription_repository,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=transcription_metrics,
    )
    transcription_queries = TranscriptionQueries(transcription_repository=transcription_repository)

    video_processing_service = VideoProcessingService(
        video_audio_extractor=FFmpegVideoAudioExtractor(),
        video_thumbnail_generator=FFmpegVideoThumbnailGenerator(),
        video_processing_task_scheduler=CeleryVideoProcessingTaskScheduler(),
        storage_service=S3StorageService(),
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
    )

    reprocess_media_handler = ReprocessMediaCommandHandler(
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics,
    )

    media_upload_validator = MediaUploadValidator(settings=MediaSettings())

    media_upload_service = MediaUploadService(
        create_media_handler=create_media_handler,
        upload_validator=media_upload_validator,
    )

    media_lifecycle_service = MediaLifecycleService(
        media_repository=media_repository,
        delete_media_handler=delete_media_handler,
        reprocess_media_handler=reprocess_media_handler,
        access_policy=media_access_policy,
    )

    media_query_service = MediaQueryService(
        media_queries=media_queries,
        access_policy=media_access_policy,
    )

    facade = MediaManagementFacade(
        queries=media_queries,
        upload_service=media_upload_service,
        lifecycle_service=media_lifecycle_service,
        query_service=media_query_service,
        access_policy=media_access_policy,
        delete_media_handler=delete_media_handler,
        reprocess_media_handler=reprocess_media_handler,
        event_bus=event_bus,
        storage_factory=storage_service_factory,
    )

    module = MediaModule(
        queries=media_queries,
        upload_service=media_upload_service,
        lifecycle_service=media_lifecycle_service,
        query_service=media_query_service,
        facade=facade,
        access_policy=media_access_policy,
        processing_service=processing_service,
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_processing_service=video_processing_service,
    )

    admin_context = MediaAdminContext(
        queries=media_queries,
        facade=facade,
    )

    return module, admin_context


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "build_media_components",
]
