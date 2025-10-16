# src/media_management/application/commands/delete_media_command_handler.py
import structlog

from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.queries.media_queries import MediaQueries
from ..services.media_storage_manager import MediaStorageManager
from .delete_media_command import DeleteMediaCommand

logger = structlog.get_logger(__name__)


class DeleteMediaCommandHandler:
    def __init__(
        self,
        media_repository: MediaRepository,
        media_queries: MediaQueries,
        media_storage_manager: MediaStorageManager,
    ):
        self.media_repository = media_repository
        self.media_queries = media_queries
        self.media_storage_manager = media_storage_manager

    async def handle(self, command: DeleteMediaCommand) -> None:
        """Orchestrates the media deletion process."""
        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            logger.warn("media.delete.not_found", media_id=str(command.media_id))
            return

        # 1. Delegate file deletion to the storage manager
        await self.media_storage_manager.delete_media_file(media)

        # 2. Delete the database record
        success = await self.media_repository.delete(command.media_id)
        if not success:
            # This case is unlikely if the media was found, but good to handle.
            logger.error("media.db_record.delete_failed", media_id=str(command.media_id))
            raise RuntimeError("Media record could not be deleted after file was handled.")

        logger.info("media.delete.completed", media_id=str(command.media_id))
