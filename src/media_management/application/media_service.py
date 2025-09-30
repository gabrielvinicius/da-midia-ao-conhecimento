# src/media_management/application/media_service.py
from uuid import UUID
from src.media_management.domain.media import Media
from .commands.create_media_command import CreateMediaCommand
from .commands.create_media_command_handler import CreateMediaCommandHandler
from .commands.delete_media_command import DeleteMediaCommand
from .commands.delete_media_command_handler import DeleteMediaCommandHandler


class MediaService:
    """Facade service to dispatch media-related commands."""
    def __init__(
        self,
        create_media_handler: CreateMediaCommandHandler,
        delete_media_handler: DeleteMediaCommandHandler, # Added dependency
    ):
        self.create_media_handler = create_media_handler
        self.delete_media_handler = delete_media_handler # Store dependency

    async def create_media(self, command: CreateMediaCommand) -> Media:
        """Dispatches the CreateMediaCommand to its handler."""
        return await self.create_media_handler.handle(command)

    async def delete_media(self, media_id: UUID) -> bool:
        """Dispatches the DeleteMediaCommand."""
        command = DeleteMediaCommand(media_id=media_id)
        return await self.delete_media_handler.handle(command)
