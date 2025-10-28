"""Service responsible for orchestrating media upload flows."""

from typing import Dict, Any, Optional
from uuid import UUID

from src.media_management.application.commands.create_media_command import CreateMediaCommand
from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.validators import MediaUploadValidator


class MediaUploadService:
    """Coordinates validation and command dispatch for uploads."""

    def __init__(
        self,
        create_media_handler: CreateMediaCommandHandler,
        upload_validator: MediaUploadValidator,
    ) -> None:
        self._create_media_handler = create_media_handler
        self._upload_validator = upload_validator

    async def create_media(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        storage_provider: str,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate input and dispatch the create media command."""

        self._upload_validator.validate(file_content, filename)

        command = CreateMediaCommand(
            user_id=str(user_id),
            file=file_content,
            filename=filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            metadata=metadata,
        )

        return await self._create_media_handler.handle(command)
