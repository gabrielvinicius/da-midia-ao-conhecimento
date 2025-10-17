# src/media_management/application/services/media_storage_manager.py
import structlog

from src.media_management.domain.media import Media
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class MediaStorageManager:
    def __init__(self, storage_service_factory: StorageServiceFactory):
        self.storage_service_factory = storage_service_factory

    async def delete_media_file(self, media: Media) -> None:
        """Deletes the physical file associated with a media entity."""
        try:
            storage_service = self.storage_service_factory(media.storage_provider)
            await storage_service.delete(media.original_file_path)
            logger.info(
                "media.file.deleted",
                path=media.original_file_path,
                provider=media.storage_provider,
            )
        except Exception as e:
            # Log the error but allow the process to continue, as the DB record is the source of truth.
            logger.error(
                "media.file.delete_failed",
                path=media.original_file_path,
                provider=media.storage_provider,
                error=str(e),
            )
            # Depending on business rules, we might want to re-raise or handle this differently.
            # For now, we just log it.
