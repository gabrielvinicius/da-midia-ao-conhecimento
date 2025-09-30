# src/media_management/application/commands/delete_media_command_handler.py
import structlog

from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import StorageServiceFactory
from .delete_media_command import DeleteMediaCommand

logger = structlog.get_logger(__name__)

class DeleteMediaCommandHandler:
    def __init__(
        self,
        media_repository: MediaRepository,
        media_queries: MediaQueries,
        storage_service_factory: StorageServiceFactory,
    ):
        self.media_repository = media_repository
        self.media_queries = media_queries
        self.storage_service_factory = storage_service_factory

    async def handle(self, command: DeleteMediaCommand) -> bool:
        """Handles the complete deletion of a media item, including its physical file."""
        logger.info("media.deletion.started", media_id=str(command.media_id))

        media_to_delete = await self.media_queries.get_by_id(str(command.media_id))
        if not media_to_delete:
            raise ValueError(f"Media with id {command.media_id} not found.")

        # 1. Delete the physical file from storage
        try:
            storage_service = self.storage_service_factory(media_to_delete.storage_provider)
            await storage_service.delete(media_to_delete.original_file_path)
            logger.info("media.file.deleted_from_storage", media_id=str(command.media_id), path=media_to_delete.original_file_path)
        except Exception as e:
            # Log the error but proceed to delete the DB record anyway.
            # In a real-world scenario, you might want a more robust retry/cleanup mechanism.
            logger.error("media.file.deletion_failed", media_id=str(command.media_id), error=str(e))

        # 2. Delete the database record
        success = await self.media_repository.delete(str(command.media_id))
        if success:
            logger.info("media.record.deleted_from_db", media_id=str(command.media_id))
        
        return success
