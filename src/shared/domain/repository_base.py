"""
Base repository interfaces - consolidating duplicated CRUD patterns
"""
from abc import ABC, abstractmethod
from typing import Optional, List, TypeVar, Generic
from uuid import UUID

T = TypeVar('T')  # Entity type

class IBaseReader(ABC, Generic[T]):
    """Base interface for read operations - eliminating duplication"""
    
    @abstractmethod
    async def find_by_id(self, entity_id: UUID) -> Optional[T]:
        """Find entity by ID."""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID, page: int = 1, limit: int = 10) -> List[T]:
        """Find entities by user ID with pagination."""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        pass

class IBaseWriter(ABC, Generic[T]):
    """Base interface for write operations - eliminating duplication"""
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save or update entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity."""
        pass

class IBaseRepository(IBaseReader[T], IBaseWriter[T]):
    """Complete repository interface combining read/write operations."""
    pass

# Media-specific extensions
class IMediaSpecificReader(IBaseReader[T]):
    """Media-specific read operations"""
    
    @abstractmethod
    async def find_by_media_id(self, media_id: UUID) -> Optional[T]:
        """Find entity by media ID."""
        pass

class IMediaRepository(IMediaSpecificReader[T], IBaseWriter[T]):
    """Repository for media-related entities (transcription, summary, etc.)"""
    pass
