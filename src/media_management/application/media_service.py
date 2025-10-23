# src/media_management/application/media_service.py
import structlog
import os
import time
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_management.domain.media import Media
from src.media_management.domain.enums import MediaType, MediaStatus
from src.media_management.application.commands.commands import DeleteMediaCommand, ReprocessMediaCommand
from src.media_management.config.settings import MediaSettings

logger = structlog.get_logger(__name__)


class MediaService:
    """Application service for orchestrating media management operations."""

    def __init__(
        self,
        media_repo: MediaRepository,
        media_queries: MediaQueries,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler,
        media_logger: StructuredMediaLogger,
        media_metrics: PrometheusMediaMetrics,
        media_settings: MediaSettings,
    ):
        self.media_repo = media_repo
        self.media_queries = media_queries
        self.delete_media_handler = delete_media_handler
        self.reprocess_media_handler = reprocess_media_handler
        self.media_logger = media_logger
        self.media_metrics = media_metrics
        self.media_settings = media_settings

    def _validate_file_size(self, file_content: bytes) -> None:
        """Validate file size against configured limits."""
        if len(file_content) > self.media_settings.max_file_size_bytes:
            raise ValueError(
                f"File too large. Max size is {self.media_settings.max_file_size_mb}MB, "
                f"got {len(file_content) / (1024 * 1024):.2f}MB"
            )

    def _get_media_type(self, filename: str) -> MediaType:
        """Determine media type from filename extension."""
        _, ext = os.path.splitext(filename or "")
        ext = ext.lower()
        
        if ext in self.media_settings.video_extensions:
            return MediaType.VIDEO
        if ext in self.media_settings.audio_extensions:
            return MediaType.AUDIO
        if ext in self.media_settings.text_extensions:
            return MediaType.TEXT
            
        raise ValueError(f"Unsupported file type: {ext}")

    async def create_media(self, user_id: UUID, file_content: bytes, filename: str, storage_provider: str) -> Media:
        """Creates a new media entry after validating the file."""
        start_time = time.monotonic()
        operation_name = "create_media"
        success = False
        error = None
        media_type = None

        try:
            logger.info(f"media_management.{operation_name}.started", user_id=str(user_id), filename=filename)

            # 1. Validate file size
            self._validate_file_size(file_content)

            # 2. Determine media type
            media_type = self._get_media_type(filename)

            # TODO: The file upload logic should be here.
            # For now, we'll just use the filename as a placeholder for the path.
            original_file_path = filename

            # 3. Create and save media record
            new_media = Media(
                user_id=user_id,
                original_file_path=original_file_path,
                media_type=media_type,
                storage_provider=storage_provider,
                status=MediaStatus.UPLOADED
            )
            await self.media_repo.add(new_media)
            success = True
            
            logger.info(f"media_management.{operation_name}.completed", media_id=str(new_media.id), user_id=str(user_id))
            return new_media

        except Exception as e:
            error = e
            logger.error(f"media_management.{operation_name}.failed", user_id=str(user_id), error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.media_logger.log_operation(
                operation=operation_name,
                media_id="N/A",
                user_id=str(user_id),
                success=success,
                duration=duration,
                error=error
            )
            await self.media_metrics.record_operation(
                operation=operation_name,
                user_id=str(user_id),
                media_type=media_type.value if media_type else "unknown",
                success=success,
                duration=duration,
                file_size_bytes=len(file_content)
            )

    async def delete_media(self, media_id: UUID) -> None:
        """Dispatches the DeleteMediaCommand."""
        command = DeleteMediaCommand(media_id=media_id)
        await self.delete_media_handler.handle(command)

    async def reprocess_media(self, media_id: UUID) -> None:
        """Dispatches the ReprocessMediaCommand."""
        command = ReprocessMediaCommand(media_id=media_id)
        await self.reprocess_media_handler.handle(command)

    async def get_media_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieves a media entry by its ID."""
        return await self.media_queries.get_by_id(media_id)

    async def list_media(self, user_id: Optional[UUID] = None, status: Optional[MediaStatus] = None) -> List[Media]:
        """Lists media entries."""
        return await self.media_queries.list_all(user_id, status)
