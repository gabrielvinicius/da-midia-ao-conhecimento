# src/media_management/application/media_service.py
import structlog
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.commands.create_media_command import CreateMediaCommand
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_management.domain.media import Media
from src.media_management.domain.enums import MediaStatus
from src.media_management.application.commands.commands import DeleteMediaCommand, ReprocessMediaCommand
from src.media_management.config.settings import MediaSettings

logger = structlog.get_logger(__name__)


class MediaService:
    """Application service for orchestrating media management operations."""

    def __init__(
        self,
        media_repo: MediaRepository,
        media_queries: MediaQueries,
        create_media_handler: CreateMediaCommandHandler,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler,
        media_logger: StructuredMediaLogger,
        media_metrics: PrometheusMediaMetrics,
        media_settings: MediaSettings,
    ):
        self.media_repo = media_repo
        self.media_queries = media_queries
        self.create_media_handler = create_media_handler
        self.delete_media_handler = delete_media_handler
        self.reprocess_media_handler = reprocess_media_handler
        self.media_logger = media_logger
        self.media_metrics = media_metrics
        self.media_settings = media_settings

    async def create_media(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        storage_provider: str,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Media:
        """Delegate media creation to the command handler."""

        command = CreateMediaCommand(
            user_id=str(user_id),
            file=file_content,
            filename=filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            metadata=metadata,
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
