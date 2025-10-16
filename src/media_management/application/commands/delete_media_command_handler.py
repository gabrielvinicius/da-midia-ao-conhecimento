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

    async def handle(self, command: DeleteMediaCommand) -> None:
        """Handles the media deletion process, including file cleanup."""
        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            # If media is not found, we can consider the operation successful.
            logger.warn("media.delete.not_found", media_id=command.media_id)
            return

        # First, try to delete the file from storage
        try:
            storage_service = self.storage_service_factory.create_storage_service(media.storage_provider)
            await storage_service.delete(media.original_file_path)
            logger.info("media.file.deleted", path=media.original_file_path)
        except Exception as e:
            # Log the error but proceed to delete the DB record anyway
            logger.error("media.file.delete_failed", path=media.original_file_path, error=str(e))

        # Then, delete the database record
        success = await self.media_repository.delete(command.media_id)
        if not success:
            # This case is unlikely if the media was found, but good to handle.
            raise RuntimeError("Media record could not be deleted after file was handled.")
