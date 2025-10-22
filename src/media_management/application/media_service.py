# src/media_management/application/media_service.py
import structlog
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.media_management.domain.interfaces import (
    IMediaRepository,
    IMediaService,
    ICreateMediaCommandHandler,
    IDeleteMediaCommandHandler,
    IReprocessMediaCommandHandler,
    IMediaQueries,
    MediaOperationLogger,
    MediaMetrics
)
from src.media_management.domain.media import Media
from src.media_management.domain.enums import MediaType, MediaStatus
from src.media_management.application.commands.commands import CreateMediaCommand, DeleteMediaCommand, ReprocessMediaCommand

logger = structlog.get_logger(__name__)


class MediaService(IMediaService):
    """Application service for orchestrating media management operations."""

    def __init__(
        self,
        media_repo: IMediaRepository,
        media_queries: IMediaQueries,
        create_media_handler: ICreateMediaCommandHandler,
        delete_media_handler: IDeleteMediaCommandHandler,
        reprocess_media_handler: IReprocessMediaCommandHandler,
        media_logger: MediaOperationLogger,
        media_metrics: MediaMetrics
    ):
        self.media_repo = media_repo
        self.media_queries = media_queries
        self.create_media_handler = create_media_handler
        self.delete_media_handler = delete_media_handler
        self.reprocess_media_handler = reprocess_media_handler
        self.media_logger = media_logger
        self.media_metrics = media_metrics

    async def create_media(self, user_id: UUID, original_file_path: str, media_type: MediaType, storage_provider: str) -> Media:
        """Creates a new media entry."""
        command = CreateMediaCommand(
            user_id=user_id,
            original_file_path=original_file_path,
            media_type=media_type,
            storage_provider=storage_provider
        )
        return await self.create_media_handler.handle(command)

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
