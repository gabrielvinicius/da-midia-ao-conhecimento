# src/media_management/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.media_management.domain.media import Media # Para referenciar a entidade Media
from src.media_management.domain.enums import MediaType, MediaStatus # Para referenciar enums


class IMediaRepository(ABC):
    """Interface for managing Media entities."""

    @abstractmethod
    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieves a media by its ID."""
        pass

    @abstractmethod
    async def add(self, media: Media) -> None:
        """Adds a new media to the repository."""
        pass

    @abstractmethod
    async def update(self, media: Media) -> None:
        """Updates an existing media in the repository."""
        pass

    @abstractmethod
    async def delete(self, media: Media) -> None:
        """Deletes a media from the repository."""
        pass

    @abstractmethod
    async def list_all(self, user_id: Optional[UUID] = None, status: Optional[MediaStatus] = None) -> List[Media]:
        """Lists all media, optionally filtered by user_id or status."""
        pass


class IMediaService(ABC):
    """Interface for the Media application service."""

    @abstractmethod
    async def create_media(self, user_id: UUID, original_file_path: str, media_type: MediaType, storage_provider: str) -> Media:
        """Creates a new media entry."""
        pass

    @abstractmethod
    async def delete_media(self, media_id: UUID) -> None:
        """Deletes a media entry."""
        pass

    @abstractmethod
    async def reprocess_media(self, media_id: UUID) -> None:
        """Reprocesses a media entry."""
        pass

    @abstractmethod
    async def get_media_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieves a media entry by its ID."""
        pass

    @abstractmethod
    async def list_media(self, user_id: Optional[UUID] = None, status: Optional[MediaStatus] = None) -> List[Media]:
        """Lists media entries."""
        pass


class ICreateMediaCommandHandler(ABC):
    """Interface for handling CreateMediaCommand."""

    @abstractmethod
    async def handle(self, command: Any) -> Media: # Usar CreateMediaCommand
        """Handles the CreateMediaCommand."""
        pass


class IDeleteMediaCommandHandler(ABC):
    """Interface for handling DeleteMediaCommand."""

    @abstractmethod
    async def handle(self, command: Any) -> None: # Usar DeleteMediaCommand
        """Handles the DeleteMediaCommand."""
        pass


class IReprocessMediaCommandHandler(ABC):
    """Interface for handling ReprocessMediaCommand."""

    @abstractmethod
    async def handle(self, command: Any) -> None: # Usar ReprocessMediaCommand
        """Handles the ReprocessMediaCommand."""
        pass


class IMediaQueries(ABC):
    """Interface for media query operations."""

    @abstractmethod
    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieves a media by its ID."""
        pass

    @abstractmethod
    async def list_all(self, user_id: Optional[UUID] = None, status: Optional[MediaStatus] = None) -> List[Media]:
        """Lists all media, optionally filtered by user_id or status."""
        pass


class MediaOperationLogger(ABC):
    """Interface for logging media management operations."""

    @abstractmethod
    async def log_operation(
        self,
        operation: str,
        media_id: str,
        user_id: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """Log media management operation with structured data."""
        pass


class MediaMetrics(ABC):
    """Interface for recording media management metrics."""

    @abstractmethod
    async def record_operation(
        self,
        operation: str,
        user_id: str,
        media_type: str,
        success: bool,
        duration: float,
        file_size_bytes: int
    ) -> None:
        """Record media management operation metrics."""
        pass