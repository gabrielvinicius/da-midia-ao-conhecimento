"""
Media State Manager - Single Responsibility: State management operations.
Follows SRP by handling only state tracking concerns for media operations.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
import structlog

from src.media_management.domain.interfaces import IMediaStateManager
from src.shared.domain.interfaces import CacheService

logger = structlog.get_logger(__name__)


class MediaStateManager(IMediaStateManager):
    """
    Manages media processing state following SRP.
    Single responsibility: Track and manage media upload/processing states.
    """
    
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service
        self._state_prefix = "media_state"
        self._default_ttl = 7200  # 2 hours (media uploads can take longer)
    
    async def update_upload_status(
        self, 
        media_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """
        Update media upload status.
        
        Args:
            media_id: Media ID
            status: Upload status (pending, uploading, completed, failed)
            error_message: Optional error message for failed status
        """
        state_data = {
            "media_id": str(media_id),
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        cache_key = f"{self._state_prefix}:{media_id}"
        ttl = self._get_ttl_for_status(status)
        
        try:
            await self._cache.set(cache_key, state_data, ttl)
            
            logger.info(
                "media.state.updated",
                media_id=str(media_id),
                status=status,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error(
                "media.state.update_failed",
                media_id=str(media_id),
                status=status,
                error=str(e)
            )
            raise
    
    async def get_upload_status(self, media_id: UUID) -> Optional[str]:
        """
        Get current media upload status.
        
        Args:
            media_id: Media ID
            
        Returns:
            Optional[str]: Current status or None if not found
        """
        cache_key = f"{self._state_prefix}:{media_id}"
        
        try:
            state_data = await self._cache.get(cache_key)
            
            if state_data:
                status = state_data.get("status")
                logger.debug(
                    "media.state.retrieved",
                    media_id=str(media_id),
                    status=status
                )
                return status
            else:
                logger.debug(
                    "media.state.not_found",
                    media_id=str(media_id)
                )
                return None
                
        except Exception as e:
            logger.error(
                "media.state.get_failed",
                media_id=str(media_id),
                error=str(e)
            )
            return None
    
    async def get_full_state(self, media_id: UUID) -> Optional[dict]:
        """
        Get full state information for a media item.
        
        Args:
            media_id: Media ID
            
        Returns:
            Optional[dict]: Full state data or None if not found
        """
        cache_key = f"{self._state_prefix}:{media_id}"
        
        try:
            state_data = await self._cache.get(cache_key)
            
            if state_data:
                logger.debug(
                    "media.state.full_retrieved",
                    media_id=str(media_id),
                    state=state_data
                )
                return state_data
            else:
                return None
                
        except Exception as e:
            logger.error(
                "media.state.get_full_failed",
                media_id=str(media_id),
                error=str(e)
            )
            return None
    
    async def cleanup_old_states(self, days_to_keep: int = 7) -> int:
        """
        Clean up old processing states.
        
        Args:
            days_to_keep: Number of days to keep state data
            
        Returns:
            int: Number of states cleaned up
        """
        # This would be implemented based on the cache backend
        # For now, return 0 as placeholder since cleanup is typically
        # handled by TTL in most cache implementations
        
        logger.info(
            "media.state.cleanup_completed",
            days_to_keep=days_to_keep,
            cleaned_count=0
        )
        
        return 0
    
    async def update_processing_progress(
        self, 
        media_id: UUID, 
        operation: str, 
        progress_percentage: float
    ) -> None:
        """
        Update processing progress for a media item.
        
        Args:
            media_id: Media ID
            operation: Operation type (transcription, summarization, etc.)
            progress_percentage: Progress percentage (0-100)
        """
        cache_key = f"{self._state_prefix}:{media_id}"
        
        try:
            # Get existing state
            existing_state = await self._cache.get(cache_key)
            if not existing_state:
                existing_state = {
                    "media_id": str(media_id),
                    "status": "processing",
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            # Update progress
            if "progress" not in existing_state:
                existing_state["progress"] = {}
            
            existing_state["progress"][operation] = {
                "percentage": progress_percentage,
                "updated_at": datetime.utcnow().isoformat()
            }
            existing_state["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated state
            await self._cache.set(cache_key, existing_state, self._default_ttl)
            
            logger.debug(
                "media.state.progress_updated",
                media_id=str(media_id),
                operation=operation,
                progress=progress_percentage
            )
            
        except Exception as e:
            logger.error(
                "media.state.progress_update_failed",
                media_id=str(media_id),
                operation=operation,
                error=str(e)
            )
    
    async def get_processing_progress(self, media_id: UUID) -> dict:
        """
        Get processing progress for a media item.
        
        Args:
            media_id: Media ID
            
        Returns:
            dict: Progress information for all operations
        """
        cache_key = f"{self._state_prefix}:{media_id}"
        
        try:
            state_data = await self._cache.get(cache_key)
            
            if state_data and "progress" in state_data:
                return state_data["progress"]
            else:
                return {}
                
        except Exception as e:
            logger.error(
                "media.state.get_progress_failed",
                media_id=str(media_id),
                error=str(e)
            )
            return {}
    
    def _get_ttl_for_status(self, status: str) -> int:
        """
        Get appropriate TTL based on status.
        
        Args:
            status: Upload/processing status
            
        Returns:
            int: TTL in seconds
        """
        ttl_map = {
            "pending": 1800,       # 30 minutes
            "uploading": 3600,     # 1 hour
            "processing": 7200,    # 2 hours
            "completed": 172800,   # 48 hours (keep success longer)
            "failed": 7200,        # 2 hours
            "cancelled": 3600      # 1 hour
        }
        
        return ttl_map.get(status, self._default_ttl)