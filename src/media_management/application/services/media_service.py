"""
Consolidated Media Service - Handles all media-related operations
Consolidates: MediaValidator, MediaFactory, MediaUploader, MediaAuthorizationService, MediaStateService
"""
import structlog
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.media_management.domain.media import Media, MediaStatus, MediaType
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.commands.commands import (
    CreateMediaCommand,
    DeleteMediaCommand,
    ReprocessMediaCommand
)
from src.media_management.application.commands.handlers import (
    CreateMediaCommandHandler,
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler
)
from src.shared.utils.id_generator import generate_id

logger = structlog.get_logger(__name__)


class MediaService:
    """
    Consolidated service for all media operations.
    Handles: CRUD, validation, upload, authorization, state management.
    """
    
    def __init__(
        self,
        media_repository: MediaRepository,
        create_media_handler: CreateMediaCommandHandler,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler
    ):
        self.media_repository = media_repository
        self.create_media_handler = create_media_handler
        self.delete_media_handler = delete_media_handler
        self.reprocess_media_handler = reprocess_media_handler

    # === MEDIA CREATION & UPLOAD ===
    
    async def create_media(
        self, 
        user_id: str, 
        file: bytes, 
        filename: str, 
        storage_provider: str,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create and upload media with validation."""
        # Validate file
        self._validate_file_content(file, filename)
        
        # Create and execute command
        command = CreateMediaCommand(
            user_id=user_id,
            file=file,
            filename=filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider
        )
        return await self.create_media_handler.handle(command)
    
    async def delete_media(self, media_id: UUID, user_id: UUID, force: bool = False) -> Dict[str, Any]:
        """Delete media with authorization check."""
        # Authorization check
        if not force:
            await self._validate_media_ownership(media_id, user_id)
        
        command = DeleteMediaCommand(media_id=media_id, user_id=user_id, force=force)
        return await self.delete_media_handler.handle(command)
    
    async def reprocess_media(self, media_id: UUID, user_id: UUID, processing_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reprocess media with ownership validation."""
        # Authorization check
        await self._validate_media_ownership(media_id, user_id)
        
        command = ReprocessMediaCommand(
            media_id=media_id,
            user_id=user_id,
            processing_options=processing_options
        )
        return await self.reprocess_media_handler.handle(command)

    # === MEDIA STATE MANAGEMENT ===
    
    async def reset_for_reprocessing(self, media_id: UUID) -> Media:
        """Reset media status for reprocessing."""
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")
        
        if media.status != MediaStatus.FAILED:
            raise ValueError(f"Media is not in FAILED state. Current: {media.status}")
        
        # Reset status
        updated_media = await self.media_repository.update_status(media_id, MediaStatus.UPLOADED)
        updated_media.error_message = None
        await self.media_repository.save(updated_media)
        
        return updated_media
    
    async def update_status(self, media_id: UUID, status: MediaStatus, error_message: Optional[str] = None) -> Media:
        """Update media processing status."""
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")
        
        updated_media = await self.media_repository.update_status(media_id, status)
        if error_message:
            updated_media.error_message = error_message
            await self.media_repository.save(updated_media)
        
        return updated_media

    # === AUTHORIZATION ===
    
    def can_user_access_media(self, media: Media, user_id: str, user_role: str = "user") -> bool:
        """Check if user can access media."""
        # Admin can access all media
        if user_role == "admin":
            return True
        
        # Users can only access their own media
        return str(media.user_id) == str(user_id)
    
    def can_user_modify_media(self, media: Media, user_id: str, user_role: str = "user") -> bool:
        """Check if user can modify media."""
        # Same logic as access for now
        return self.can_user_access_media(media, user_id, user_role)

    # === VALIDATION ===
    
    def _validate_file_content(self, file_data: bytes, filename: str) -> None:
        """Validate uploaded file."""
        if not file_data:
            raise ValueError("File content is empty")
        
        if len(file_data) > 100 * 1024 * 1024:  # 100MB
            raise ValueError("File size exceeds maximum limit (100MB)")
        
        if len(file_data) < 1024:  # 1KB
            raise ValueError("File size is too small (minimum 1KB)")
        
        # Validate file extension
        media_type = self.get_media_type(filename)
        if not media_type:
            raise ValueError("Unsupported file format")
    
    def get_media_type(self, filename: str) -> Optional[MediaType]:
        """Determine media type from filename."""
        if not filename:
            return None
        
        extension = filename.lower().split('.')[-1]
        
        video_extensions = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
        audio_extensions = {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'}
        
        if extension in video_extensions:
            return MediaType.VIDEO
        elif extension in audio_extensions:
            return MediaType.AUDIO
        else:
            return None
    
    async def _validate_media_ownership(self, media_id: UUID, user_id: UUID) -> None:
        """Validate user owns the media."""
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")
        
        if str(media.user_id) != str(user_id):
            raise PermissionError("User does not own this media")

    # === FACTORY METHODS ===
    
    def create_media_entity(
        self,
        media_id: UUID,
        user_id: str,
        file_path: str,
        media_type: MediaType,
        storage_provider: str,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None
    ) -> Media:
        """Create a new Media entity."""
        return Media(
            id=media_id,
            user_id=UUID(user_id),
            original_file_path=file_path,
            media_type=media_type,
            status=MediaStatus.UPLOADED,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider
        )

    # === QUERY METHODS ===
    
    async def get_media_by_id(self, media_id: UUID) -> Optional[Media]:
        """Get media by ID."""
        return await self.media_repository.get_by_id(media_id)
    
    async def list_user_media(self, user_id: str) -> List[Media]:
        """List all media for a user."""
        return await self.media_repository.find_by_user_id(user_id)
    
    async def list_media_by_status(self, status: MediaStatus) -> List[Media]:
        """List media by processing status."""
        return await self.media_repository.find_by_status(status)
    
    async def count_user_media(self, user_id: str) -> int:
        """Count media for a user."""
        return await self.media_repository.count_by_user_id(user_id)
    
    async def get_media_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get media statistics."""
        if user_id:
            total = await self.count_user_media(user_id)
            by_status = {}
            for status in MediaStatus:
                count = await self.media_repository.count_by_user_and_status(user_id, status)
                by_status[status.value] = count
        else:
            total = await self.media_repository.count_all()
            by_status = {}
            for status in MediaStatus:
                count = await self.media_repository.count_by_status(status)
                by_status[status.value] = count
        
        return {
            "total": total,
            "by_status": by_status
        }