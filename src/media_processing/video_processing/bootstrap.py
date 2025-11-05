# src/video_processing/bootstrap.py
from dataclasses import dataclass
from typing import Optional

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Consolidated Service
from src.media_processing.video_processing.application.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.video_processing.infrastructure.metrics import (
    PrometheusVideoProcessingMetrics,
)
from src.media_processing.video_processing.infrastructure.task_scheduler import (
    CeleryVideoProcessingTaskScheduler,
)

# Concrete Implementations
from src.media_processing.video_processing.infrastructure.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.media_processing.video_processing.infrastructure.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory

# TODO: Adicionar logger e metrics específicos para video_processing


class VideoProcessingContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    storage_factory: providers.Provider[StorageServiceFactory] = providers.Dependency()
    storage_provider = providers.Dependency(default="local")

    # Infrastructure Services
    video_audio_extractor = providers.Factory(FFmpegVideoAudioExtractor)
    video_thumbnail_generator = providers.Factory(FFmpegVideoThumbnailGenerator)
    video_processing_task_scheduler = providers.Factory(CeleryVideoProcessingTaskScheduler)
    video_processing_metrics = providers.Singleton(PrometheusVideoProcessingMetrics)

    # Consolidated Application Service
    video_processing_service = providers.Factory(
        VideoProcessingService,
        video_audio_extractor=video_audio_extractor,
        video_thumbnail_generator=video_thumbnail_generator,
        video_processing_task_scheduler=video_processing_task_scheduler,
        storage_factory=storage_factory,
        default_storage_provider=storage_provider,
        video_processing_metrics=video_processing_metrics,
    )


@dataclass
class VideoProcessingModule:
    service: VideoProcessingService
    task_scheduler: CeleryVideoProcessingTaskScheduler


async def build_video_processing_module(
    session: AsyncSession,
    *,
    storage_factory: Optional[StorageServiceFactory] = None,
    storage_provider: str = "local",
) -> VideoProcessingModule:
    storage_factory = storage_factory or StorageServiceFactory()
    container = VideoProcessingContainer(
        db=session,
        storage_factory=storage_factory,
        storage_provider=storage_provider,
    )
    module = VideoProcessingModule(
        service=container.video_processing_service(),
        task_scheduler=container.video_processing_task_scheduler(),
    )
    return module


__all__ = [
    "VideoProcessingContainer",
    "VideoProcessingModule",
    "build_video_processing_module",
]
