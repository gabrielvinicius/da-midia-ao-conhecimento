# src/video_processing/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.video_processing.infrastructure.video_audio_extractor import FFmpegVideoAudioExtractor
from src.video_processing.infrastructure.video_thumbnail_generator import FFmpegVideoThumbnailGenerator
from src.video_processing.infrastructure.task_scheduler import CeleryVideoProcessingTaskScheduler
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
# TODO: Adicionar logger e metrics específicos para video_processing

# Consolidated Service
from src.video_processing.application.video_processing_service import VideoProcessingService

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
