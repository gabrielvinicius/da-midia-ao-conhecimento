# src/video_processing/application/commands/handlers.py
import structlog
from typing import Dict, Any
from uuid import UUID
import time # Adicionar para calcular duração

from src.video_processing.domain.interfaces import IVideoAudioExtractor, IVideoThumbnailGenerator
from src.video_processing.application.commands.commands import ProcessVideoCommand
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService # Para baixar o arquivo de vídeo

logger = structlog.get_logger(__name__)


class ProcessVideoCommandHandler:
    """Handler for processing a video."""

    def __init__(
        self,
        video_audio_extractor: IVideoAudioExtractor,
        video_thumbnail_generator: IVideoThumbnailGenerator,
        storage_service: S3StorageService, # Injetar serviço de armazenamento
        # TODO: Adicionar logger e metrics específicos para video_processing
    ):
        self.video_audio_extractor = video_audio_extractor
        self.video_thumbnail_generator = video_thumbnail_generator
        self.storage_service = storage_service

    async def handle(self, command: ProcessVideoCommand) -> Dict[str, Any]:
        start_time = time.monotonic()
        operation_name = "process_video_command"
        success = False
        error = None

        logger.info(
            f"video_processing.{operation_name}.started",
            media_id=command.media_id,
            file_path=command.file_path
        )
        try:
            # 1. Get the video file
            video_data = await self.storage_service.download_file(command.file_path)
            
            # 2. Extract audio
            audio_result = await self.video_audio_extractor.extract_audio(
                video_data=video_data,
                filename=command.file_path,
                output_format='wav' # Ou outro formato configurável
            )
            
            # 3. Generate thumbnail
            thumbnail_result = await self.video_thumbnail_generator.generate_thumbnail(
                video_data=video_data,
                filename=command.file_path,
                size='medium', # Ou outro tamanho configurável
                timestamp=5.0 # Ou outro timestamp configurável
            )
            
            success = True
            logger.info(
                f"video_processing.{operation_name}.completed",
                media_id=command.media_id
            )
            return {
                "success": True,
                "media_id": command.media_id,
                "audio_extraction_result": audio_result,
                "thumbnail_generation_result": thumbnail_result,
                "message": "Video processed successfully"
            }
        except Exception as e:
            error = e
            logger.error(
                f"video_processing.{operation_name}.failed",
                media_id=command.media_id,
                error=str(e)
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            # TODO: Adicionar logging e métricas aqui
            # await self.video_processing_logger.log_operation(...) # Placeholder
            # await self.video_processing_metrics.record_operation(...) # Placeholder
