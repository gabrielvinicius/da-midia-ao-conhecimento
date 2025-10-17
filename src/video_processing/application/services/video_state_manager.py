"""
Video State Manager - Single Responsibility: State management operations.
Follows SRP by handling only state tracking concerns.
"""
from typing import Optional
from datetime import datetime
import structlog

from src.video_processing.domain.interfaces import IVideoStateManager
from src.shared.domain.interfaces import CacheService

logger = structlog.get_logger(__name__)


class VideoStateManager(IVideoStateManager):
    """
    Manages video processing state following SRP.
    Single responsibility: Track and manage video processing states.
    """
    
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service
        self._state_prefix = "video_state"
        self._default_ttl = 7200  # 2 hours (videos take longer to process)
    
    async def update_status(
        self, 
        media_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """
        Update video processing status.
        
        Args:
            media_id: Media ID
            status: Processing status (pending, processing, completed, failed)
            error_message: Optional error message for failed status
        """
        state_data = {
            "media_id": media_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        cache_key = f"{self._state_prefix}:{media_id}"
        ttl = self._get_ttl_for_status(status)
        
        try:
            await self._cache.set(cache_key, state_data, ttl)
            
            logger.info(
                "video.state.updated",
                media_id=media_id,
                status=status,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error(
                "video.state.update_failed",
                media_id=media_id,
                status=status,
                error=str(e)
            )
            raise
    
    async def get_status(self, media_id: str) -> Optional[str]:
        """
        Get current video processing status.
        
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
                    "video.state.retrieved",
                    media_id=media_id,
                    status=status
                )
                return status
            else:
                logger.debug(
                    "video.state.not_found",
                    media_id=media_id
                )
                return None
                
        except Exception as e:
            logger.error(
                "video.state.get_failed",
                media_id=media_id,
                error=str(e)
            )
            return None
    
    async def get_full_state(self, media_id: str) -> Optional[dict]:
        """
        Get full state information for a video.
        
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
                    "video.state.full_retrieved",
                    media_id=media_id,
                    state=state_data
                )
                return state_data
            else:
                return None
                
        except Exception as e:
            logger.error(
                "video.state.get_full_failed",
                media_id=media_id,
                error=str(e)
            )
            return None
    
    def _get_ttl_for_status(self, status: str) -> int:
        """
        Get appropriate TTL based on status.
        
        Args:
            status: Processing status
            
        Returns:
            int: TTL in seconds
        """
        ttl_map = {
            "pending": 3600,      # 1 hour
            "processing": 7200,   # 2 hours (videos take longer)
            "completed": 172800,  # 48 hours (keep success longer)
            "failed": 7200,       # 2 hours
            "cancelled": 3600     # 1 hour
        }
        
        return ttl_map.get(status, self._default_ttl)