"""
Domain interfaces for media management module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from src.media_management.domain.media import Media, MediaType


class IMediaRepository(ABC):
    """Interface for media repository operations."""
    
    @abstractmethod
    async def save(self, media: Media) -> Media:
        """Save or update a media."""
        pass
    
    @abstractmethod
    async def find_by_id(self, media_id: UUID) -> Optional[Media]:
        """Find media by ID."""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID, page: int = 1, limit: int = 10) -> List[Media]:
        """Find media by user ID with pagination."""
        pass
    
    @abstractmethod
    async def delete(self, media_id: UUID) -> bool:
        """Delete a media."""
        pass


class IMediaValidator(ABC):
    """Interface for media validation operations."""
    
    @abstractmethod
    def validate_file_content(self, file: bytes, filename: str) -> None:
        """Validate file content and format."""
        pass
    
    @abstractmethod
    def validate_file_size(self, file: bytes) -> None:
        """Validate file size constraints."""
        pass
    
    @abstractmethod
    def validate_file_type(self, filename: str) -> None:
        """Validate file type is supported."""
        pass
    
    @abstractmethod
    def get_media_type(self, filename: str) -> MediaType:
        """Determine media type from filename."""
        pass


class IMediaUploader(ABC):
    """Interface for media upload operations."""
    
    @abstractmethod
    async def upload(
        self,
        file: bytes,
        user_id: UUID,
        media_id: UUID,
        filename: str,
        storage_provider: str,
    ) -> str:
        """Upload media file to storage."""
        pass


class IMediaEventManager(ABC):
    """Interface for media event publishing."""
    
    @abstractmethod
    async def publish_media_uploaded(self, media: Media) -> None:
        """Publish media uploaded event."""
        pass
    
    @abstractmethod
    async def publish_media_processed(self, media: Media) -> None:
        """Publish media processed event."""
        pass
    
    @abstractmethod
    async def publish_media_failed(self, media: Media, error: str) -> None:
        """Publish media processing failed event."""
        pass


class IMediaMetricsService(ABC):
    """Interface for media metrics operations."""
    
    @abstractmethod
    def record_upload_success(self, media_id: UUID, duration: float, provider: str) -> None:
        """Record successful upload metrics."""
        pass
    
    @abstractmethod
    def record_upload_failure(self) -> None:
        """Record upload failure metrics."""
        pass
    
    @abstractmethod
    def record_processing_duration(self, media_id: UUID, duration: float, operation: str) -> None:
        """Record processing duration metrics."""
        pass


class IMediaFactory(ABC):
    """Interface for media entity creation."""
    
    @abstractmethod
    def create(
        self,
        media_id: UUID,
        user_id: UUID,
        file_path: str,
        media_type: MediaType,
        storage_provider: str,
        transcription_provider: str,
        summarization_provider: str,
    ) -> Media:
        """Create a new media entity."""
        pass