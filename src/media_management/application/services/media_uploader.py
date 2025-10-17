# src/media_management/application/services/media_uploader.py
from uuid import UUID
import structlog

from src.media_management.domain.interfaces import IMediaUploader
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class MediaUploader(IMediaUploader):
    """
    Media upload service following SOLID principles.
    
    Single Responsibility: Handle media file uploads to storage.
    Open/Closed: Open for extension via storage providers.
    Dependency Inversion: Depends on storage service abstraction.
    """
    
    def __init__(self, storage_service_factory: StorageServiceFactory):
        self.storage_service_factory = storage_service_factory

    async def upload(
        self,
        file: bytes,
        user_id: UUID,
        media_id: UUID,
        filename: str,
        storage_provider: str,
    ) -> str:
        storage_service = self.storage_service_factory(storage_provider)
        file_path = f"media/{user_id}/{media_id}/{filename}"

        logger.info(
            "media.upload.storage.started",
            media_id=str(media_id),
            provider=storage_provider,
            path=file_path,
        )

        await storage_service.upload(file_path, file)

        logger.info(
            "media.upload.storage.completed",
            media_id=str(media_id),
            provider=storage_provider,
        )
        return file_path
