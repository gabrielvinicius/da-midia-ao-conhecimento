# src/media_management/application/media_service.py
from src.media_management.domain.media import Media
from .commands.create_media_command import CreateMediaCommand
from .commands.create_media_command_handler import CreateMediaCommandHandler


class MediaService:
    """Facade service to dispatch media-related commands."""
    def __init__(self, create_media_handler: CreateMediaCommandHandler):
        self.create_media_handler = create_media_handler

    async def create_media(self, command: CreateMediaCommand) -> Media:
        """Dispatches the CreateMediaCommand to its handler."""
        return await self.create_media_handler.handle(command)
