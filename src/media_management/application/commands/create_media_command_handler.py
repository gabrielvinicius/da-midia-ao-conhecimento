# src/media_management/application/commands/create_media_command_handler.py
import os
import time
from uuid import uuid4
import structlog

from src.media_management.domain.media import Media, MediaType, MediaStatus
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import MediaUploaded
from src.metrics.application.metrics_service import MetricsService
from ..config.settings import MediaSettings
from .create_media_command import CreateMediaCommand

logger = structlog.get_logger(__name__)

class CreateMediaCommandHandler:
    def __init__(
        self,
        media_repository: MediaRepository,
        storage_service_factory: StorageServiceFactory,
        event_bus: EventBus,
        metrics_service: MetricsService,
        settings: MediaSettings,
    ):
        self.media_repository = media_repository
        self.storage_service_factory = storage_service_factory
        self.event_bus = event_bus
        self.metrics_service = metrics_service
        self.settings = settings

    def _get_media_type(self, filename: str) -> MediaType:
        _, ext = os.path.splitext(filename or "")
        ext = ext.lower()
        if ext in self.settings.video_extensions:
            return MediaType.VIDEO
        if ext in self.settings.audio_extensions:
            return MediaType.AUDIO
        if ext in self.settings.text_extensions:
            return MediaType.TEXT
        raise ValueError(f"Unsupported file type: {ext}")

    async def handle(self, command: CreateMediaCommand) -> Media:
        start_time = time.time()
        media_id = uuid4()
        
        try:
            # 1. Validation Logic now lives in the handler
            if not command.filename:
                raise ValueError("File must have a filename.")
            if not command.file:
                raise ValueError("File content is empty.")

            media_type = self._get_media_type(command.filename)

            if len(command.file) > self.settings.max_file_size_bytes:
                raise ValueError(f"File too large. Max size is {self.settings.max_file_size_mb}MB")

            # 2. Process and Persist
            storage_service = self.storage_service_factory(command.storage_provider)
            file_path = f"media/{command.user_id}/{media_id}/{command.filename}"
            logger.info("media.upload.started", media_id=str(media_id), provider=command.storage_provider)

            await storage_service.upload(file_path, command.file)

            media = Media(
                id=media_id,
                user_id=command.user_id,
                original_file_path=file_path,
                media_type=media_type,
                status=MediaStatus.UPLOADED,
                storage_provider=command.storage_provider,
                transcription_provider=command.transcription_provider,
                summarization_provider=command.summarization_provider
            )
            saved_media = await self.media_repository.save(media)

            # 3. Publish Event
            event = MediaUploaded(
                media_id=str(saved_media.id),
                user_id=str(saved_media.user_id),
                media_type=saved_media.media_type,
                file_path=saved_media.original_file_path,
                storage_provider=saved_media.storage_provider,
                transcription_provider=saved_media.transcription_provider,
                summarization_provider=saved_media.summarization_provider
            )
            await self.event_bus.publish(event)

            # 4. Record Metrics
            duration = time.time() - start_time
            self.metrics_service.increment_media_upload('success')
            self.metrics_service.observe_upload_duration(media_id=str(saved_media.id), duration=duration, provider=storage_service.provider_name)

            logger.info("media.upload.completed", media_id=str(saved_media.id), duration=duration)
            return saved_media

        except Exception as e:
            self.metrics_service.increment_media_upload('failure')
            logger.error("media.upload.failed", media_id=str(media_id), error=str(e))
            raise ValueError(f"Media upload failed: {str(e)}") from e
