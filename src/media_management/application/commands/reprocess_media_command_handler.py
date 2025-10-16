# src/media_management/application/commands/reprocess_media_command_handler.py
import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from ..services.media_state_service import MediaStateService
from ..services.media_event_manager import MediaEventManager
from .reprocess_media_command import ReprocessMediaCommand

logger = structlog.get_logger(__name__)


class ReprocessMediaCommandHandler:
    def __init__(
        self,
        media_queries: MediaQueries,
        media_repository: MediaRepository,
        media_state_service: MediaStateService,
        media_event_manager: MediaEventManager,
    ):
        self.media_queries = media_queries
        self.media_repository = media_repository
        self.media_state_service = media_state_service
        self.media_event_manager = media_event_manager

    async def handle(self, command: ReprocessMediaCommand) -> None:
        """Orchestrates the media reprocessing workflow."""
        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            raise ValueError("Media not found.")

        # 1. Delegate state change and validation
        updated_media = self.media_state_service.reset_for_reprocessing(media)

        # 2. Persist the change
        await self.media_repository.save(updated_media)

        # 3. Delegate event publishing
        await self.media_event_manager.publish_media_uploaded(updated_media)

        logger.info("media.reprocessing.initiated", media_id=str(command.media_id))
