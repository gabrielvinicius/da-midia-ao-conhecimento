# src/media_management/application/media_service.py
from uuid import UUID
from src.media_management.domain.media import Media
from .commands.create_media_command import CreateMediaCommand
from .commands.create_media_command_handler import CreateMediaCommandHandler
from .commands.delete_media_command import DeleteMediaCommand
from .commands.delete_media_command_handler import DeleteMediaCommandHandler
from .commands.reprocess_media_command import ReprocessMediaCommand
from .commands.reprocess_media_command_handler import ReprocessMediaCommandHandler


class MediaService:
    """Facade service to dispatch media-related commands."""
    def __init__(
        self,
        create_media_handler: CreateMediaCommandHandler,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler, # Added dependency
    ):
        self.create_media_handler = create_media_handler
        self.delete_media_handler = delete_media_handler
        self.reprocess_media_handler = reprocess_media_handler # Store dependency

    async def create_media(self, command: CreateMediaCommand) -> Media:
        """Dispatches the CreateMediaCommand to its handler."""
        return await self.create_media_handler.handle(command)

    async def delete_media(self, media_id: UUID) -> bool:
        """Dispatches the DeleteMediaCommand."""
        command = DeleteMediaCommand(media_id=media_id)
        return await self.delete_media_handler.handle(command)

    async def reprocess_media(self, media_id: UUID) -> None:
        """Dispatches the ReprocessMediaCommand."""
        command = ReprocessMediaCommand(media_id=media_id)
        await self.reprocess_media_handler.handle(command)
