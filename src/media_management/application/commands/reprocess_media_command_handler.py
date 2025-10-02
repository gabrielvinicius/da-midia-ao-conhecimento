# src/media_management/application/commands/reprocess_media_command_handler.py
import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.domain.media import MediaStatus
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import MediaUploaded
from .reprocess_media_command import ReprocessMediaCommand

logger = structlog.get_logger(__name__)

class ReprocessMediaCommandHandler:
    def __init__(
        self,
        media_queries: MediaQueries,
        media_repository: MediaRepository,
        event_bus: EventBus,
    ):
        self.media_queries = media_queries
        self.media_repository = media_repository
        self.event_bus = event_bus

    async def handle(self, command: ReprocessMediaCommand) -> None:
        """Handles the media reprocessing request."""
        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            raise ValueError("Media not found.")

        if media.status != MediaStatus.FAILED:
            raise ValueError(f"Media is not in a FAILED state. Current status: {media.status}")

        # Reset status to re-trigger processing
        media.status = MediaStatus.UPLOADED
        media.error_message = None
        await self.media_repository.save(media)

        # Re-publish the original MediaUploaded event to trigger the pipeline again
        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(media.user_id),
            media_type=media.media_type,
            file_path=media.original_file_path,
            storage_provider=media.storage_provider,
            transcription_provider=media.transcription_provider,
            summarization_provider=media.summarization_provider
        )
        
        await self.event_bus.publish(event)
        logger.info("media.reprocessing.initiated", media_id=command.media_id)
