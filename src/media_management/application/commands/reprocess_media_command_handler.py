# src/media_management/application/commands/reprocess_media_command_handler.py
import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import MediaUploaded
from src.media_management.domain.media import MediaStatus
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
        """Handles the media reprocessing logic."""
        logger.info("media.reprocessing.started", media_id=str(command.media_id))

        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        if media.status != MediaStatus.FAILED:
            raise ValueError(f"Media with id {command.media_id} is not in a FAILED state.")

        # 1. Reset the media status to PENDING
        media.reset_status()
        await self.media_repository.save(media)
        logger.info("media.reprocessing.status_reset", media_id=str(command.media_id))

        # 2. Re-publish the initial event to trigger the pipeline again
        await self.event_bus.publish(
            MediaUploaded(
                media_id=str(media.id),
                user_id=str(media.user_id),
                media_type=media.media_type,
                file_path=media.original_file_path,
                storage_provider=media.storage_provider,
            )
        )
        logger.info("media.reprocessing.event_published", media_id=str(command.media_id))
