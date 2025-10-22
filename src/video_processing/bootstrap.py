# src/video_processing/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.video_processing.domain.interfaces import IVideoAudioExtractor, IVideoThumbnailGenerator, IVideoProcessingTaskScheduler
from src.video_processing.infrastructure.video_audio_extractor import FFmpegVideoAudioExtractor
from src.video_processing.infrastructure.video_thumbnail_generator import FFmpegVideoThumbnailGenerator
from src.video_processing.infrastructure.task_scheduler import CeleryVideoProcessingTaskScheduler
from src.video_processing.application.commands.handlers import ProcessVideoCommandHandler
from src.video_processing.application.video_processing_service import VideoProcessingService
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService

class VideoProcessingContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()
    storage_service: providers.Provider[S3StorageService] = providers.Singleton(S3StorageService)

    # Implementações concretas das interfaces de domínio
    video_audio_extractor: providers.Provider[IVideoAudioExtractor] = providers.Factory(
        FFmpegVideoAudioExtractor
    )
    video_thumbnail_generator: providers.Provider[IVideoThumbnailGenerator] = providers.Factory(
        FFmpegVideoThumbnailGenerator
    )
    video_processing_task_scheduler: providers.Provider[IVideoProcessingTaskScheduler] = providers.Factory(
        CeleryVideoProcessingTaskScheduler
    )

    # Command Handlers
    process_video_command_handler: providers.Provider[ProcessVideoCommandHandler] = providers.Factory(
        ProcessVideoCommandHandler,
        video_audio_extractor=video_audio_extractor,
        video_thumbnail_generator=video_thumbnail_generator,
        storage_service=storage_service,
        # TODO: Adicionar logger e metrics específicos para video_processing
    )

    # Serviços de Aplicação
    video_processing_service: providers.Provider[VideoProcessingService] = providers.Factory(
        VideoProcessingService,
        video_audio_extractor=video_audio_extractor,
        video_thumbnail_generator=video_thumbnail_generator,
        video_processing_task_scheduler=video_processing_task_scheduler,
        # TODO: Adicionar video_processing_logger, video_processing_metrics
    )
