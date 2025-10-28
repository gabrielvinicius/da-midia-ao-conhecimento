# src/video_processing/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.video_processing.infrastructure.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.video_processing.infrastructure.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.video_processing.infrastructure.task_scheduler import (
    CeleryVideoProcessingTaskScheduler,
)
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.shared.events.event_bus import EventBus
# TODO: Adicionar logger e metrics específicos para video_processing

# Consolidated Service
from src.video_processing.application.video_processing_service import (
    VideoProcessingService,
)
from src.video_processing.application.event_handlers import (
    register_event_handlers as register_video_handlers,
)


class VideoProcessingContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    storage_service: providers.Provider[S3StorageService] = providers.Singleton(S3StorageService)

    # Infrastructure Services
    video_audio_extractor = providers.Factory(FFmpegVideoAudioExtractor)
    video_thumbnail_generator = providers.Factory(FFmpegVideoThumbnailGenerator)
    video_processing_task_scheduler = providers.Factory(CeleryVideoProcessingTaskScheduler)
    # TODO: Adicionar video_processing_logger, video_processing_metrics

    # Consolidated Application Service
    video_processing_service = providers.Factory(
        VideoProcessingService,
        video_audio_extractor=video_audio_extractor,
        video_thumbnail_generator=video_thumbnail_generator,
        video_processing_task_scheduler=video_processing_task_scheduler,
        storage_service=storage_service,
        # TODO: Adicionar video_processing_logger, video_processing_metrics
    )


@dataclass
class VideoProcessingModule:
    service: VideoProcessingService
    task_scheduler: CeleryVideoProcessingTaskScheduler


async def build_video_processing_module(
    session: AsyncSession,
    *,
    event_bus: EventBus,
) -> VideoProcessingModule:
    container = VideoProcessingContainer(db=session)
    module = VideoProcessingModule(
        service=container.video_processing_service(),
        task_scheduler=container.video_processing_task_scheduler(),
    )
    await register_video_handlers(event_bus, module.task_scheduler)
    return module


__all__ = [
    "VideoProcessingContainer",
    "VideoProcessingModule",
    "build_video_processing_module",
]
