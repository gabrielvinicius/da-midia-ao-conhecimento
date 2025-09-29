# src/media_management/application/commands/create_media_command_handler.py
import os
from uuid import uuid4
import structlog

from src.media_management.domain.media import Media, MediaType, MediaStatus
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import MediaUploaded
from .create_media_command import CreateMediaCommand

logger = structlog.get_logger(__name__)


def _get_media_type_from_filename(filename: str) -> MediaType:
    """Determines the media type based on the file extension."""
    _, ext = os.path.splitext(filename or "")
    ext = ext.lower()
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        return MediaType.VIDEO
    if ext in [".mp3", ".wav", ".m4a", ".flac"]:
        return MediaType.AUDIO
    if ext in [".txt", ".md"]:
        return MediaType.TEXT
    raise ValueError(f"Unsupported file type: {ext}")


class CreateMediaCommandHandler:
    def __init__(
        self,
        media_repository: MediaRepository,
        storage_service_factory: StorageServiceFactory,
        event_bus: EventBus,
    ):
        self.media_repository = media_repository
        self.storage_service_factory = storage_service_factory
        self.event_bus = event_bus

    async def handle(self, command: CreateMediaCommand) -> Media:
        """Handles the media upload, persistence, and event publication."""
        media_id = uuid4()
        media_type = _get_media_type_from_filename(command.filename)
        storage_service = self.storage_service_factory(command.storage_provider)

        file_path = f"media/{command.user_id}/{media_id}/{command.filename}"
        logger.info("media.upload.started", media_id=str(media_id), media_type=media_type.value)

        await storage_service.upload(file_path, command.file)

        media = Media(
            id=media_id,
            user_id=command.user_id,
            original_file_path=file_path,
            media_type=media_type,
            status=MediaStatus.UPLOADED,
        )
        saved_media = await self.media_repository.save(media)

        event = MediaUploaded(
            media_id=str(saved_media.id),
            user_id=str(saved_media.user_id),
            media_type=saved_media.media_type,
            file_path=saved_media.original_file_path,
        )
        await self.event_bus.publish(event)

        logger.info("media.upload.completed", media_id=str(saved_media.id))
        return saved_media
