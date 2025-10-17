# src/media_management/application/commands/create_media_command_handler.py
import time
from uuid import uuid4
import structlog

from src.media_management.domain.media import Media
from src.media_management.domain.interfaces import (
    IMediaRepository,
    IMediaValidator,
    IMediaUploader,
    IMediaFactory,
    IMediaEventManager,
    IMediaMetricsService
)
from .create_media_command import CreateMediaCommand

logger = structlog.get_logger(__name__)


class CreateMediaCommandHandler:
    """
    Command handler for media creation.
    
    Follows SOLID principles:
    - SRP: Handles only media creation orchestration
    - OCP: Open for extension through interface implementations
    - LSP: Depends on interfaces, not concrete implementations
    - ISP: Uses specific interfaces for each responsibility
    - DIP: Depends on abstractions, not concretions
    """
    
    def __init__(
        self,
        media_repository: IMediaRepository,
        media_validator: IMediaValidator,
        media_uploader: IMediaUploader,
        media_factory: IMediaFactory,
        media_event_manager: IMediaEventManager,
        media_metrics_service: IMediaMetricsService,
    ):
        self.media_repository = media_repository
        self.media_validator = media_validator
        self.media_uploader = media_uploader
        self.media_factory = media_factory
        self.media_event_manager = media_event_manager
        self.media_metrics_service = media_metrics_service

    async def handle(self, command: CreateMediaCommand) -> Media:
        start_time = time.time()
        media_id = uuid4()
        logger.info("media.upload.started", media_id=str(media_id))

        try:
            # 1. Validate
            self.media_validator.validate_file_content(command.file, command.filename)
            media_type = self.media_validator.get_media_type(command.filename)

            # 2. Upload
            file_path = await self.media_uploader.upload(
                file=command.file,
                user_id=command.user_id,
                media_id=media_id,
                filename=command.filename,
                storage_provider=command.storage_provider,
            )

            # 3. Create Domain Object
            media = self.media_factory.create(
                media_id=media_id,
                user_id=command.user_id,
                file_path=file_path,
                media_type=media_type,
                storage_provider=command.storage_provider,
                transcription_provider=command.transcription_provider,
                summarization_provider=command.summarization_provider,
            )

            # 4. Persist
            saved_media = await self.media_repository.save(media)

            # 5. Publish Event
            await self.media_event_manager.publish_media_uploaded(saved_media)

            # 6. Record Metrics
            duration = time.time() - start_time
            self.media_metrics_service.record_upload_success(
                media_id=saved_media.id,
                duration=duration,
                provider=command.storage_provider,
            )

            logger.info("media.upload.completed", media_id=str(saved_media.id), duration=duration)
            return saved_media

        except Exception as e:
            self.media_metrics_service.record_upload_failure()
            logger.error("media.upload.failed", media_id=str(media_id), error=str(e))
            # Re-raise as a more specific domain exception if applicable, or a generic one
            raise ValueError(f"Media upload failed: {str(e)}") from e