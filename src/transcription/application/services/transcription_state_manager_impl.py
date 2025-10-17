"""
Transcription State Manager Implementation - Single Responsibility: State management.
Follows SRP by handling only state tracking concerns.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
import structlog

from src.transcription.domain.interfaces import ITranscriptionStateManager
from src.shared.domain.interfaces import CacheService

logger = structlog.get_logger(__name__)


class TranscriptionStateManagerImpl(ITranscriptionStateManager):
    """
    Implements transcription processing state management following SRP.
    Single responsibility: Track and manage transcription processing states.
    """
    
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service
        self._state_prefix = "transcription_state"
        self._default_ttl = 3600  # 1 hour
    
    async def update_status(
        self, 
        transcription_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update transcription processing status."""
        state_data = {
            "transcription_id": str(transcription_id),
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        cache_key = f"{self._state_prefix}:{transcription_id}"
        ttl = self._get_ttl_for_status(status)
        
        await self._cache.set(cache_key, state_data, ttl)
        
        logger.info(
            "transcription.state.updated",
            transcription_id=str(transcription_id),
            status=status
        )
    
    async def get_status(self, transcription_id: UUID) -> Optional[str]:
        """Get current transcription processing status."""
        cache_key = f"{self._state_prefix}:{transcription_id}"
        state_data = await self._cache.get(cache_key)
        
        return state_data.get("status") if state_data else None
    
    def _get_ttl_for_status(self, status: str) -> int:
        """Get appropriate TTL based on status."""
        ttl_map = {
            "pending": 1800,      # 30 minutes
            "processing": 3600,   # 1 hour
            "completed": 86400,   # 24 hours
            "failed": 3600,       # 1 hour
        }
        return ttl_map.get(status, self._default_ttl)