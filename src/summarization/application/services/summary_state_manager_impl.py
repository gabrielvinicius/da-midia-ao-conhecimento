"""
Summary State Manager Implementation - Single Responsibility: State management operations.
Follows SRP by handling only state tracking concerns.
"""
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime, timedelta
import structlog

from src.summarization.domain.interfaces import ISummaryStateManager
from src.shared.domain.interfaces import CacheService

logger = structlog.get_logger(__name__)


class SummaryStateManagerImpl(ISummaryStateManager):
    """
    Implements summary processing state management following SRP.
    Single responsibility: Track and manage summary processing states.
    """
    
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service
        self._state_prefix = "summary_state"
        self._default_ttl = 3600  # 1 hour
    
    async def update_status(
        self, 
        summary_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update summary processing status."""
        state_data = {
            "summary_id": str(summary_id),
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        cache_key = f"{self._state_prefix}:{summary_id}"
        ttl = self._get_ttl_for_status(status)
        
        await self._cache.set(cache_key, state_data, ttl)
        
        logger.info(
            "summary.state.updated",
            summary_id=str(summary_id),
            status=status
        )
    
    async def get_status(self, summary_id: UUID) -> Optional[str]:
        """Get current summary processing status."""
        cache_key = f"{self._state_prefix}:{summary_id}"
        state_data = await self._cache.get(cache_key)
        
        return state_data.get("status") if state_data else None
    
    async def cleanup_old_states(self, days_to_keep: int = 7) -> int:
        """Clean up old processing states."""
        # TTL-based cleanup is automatic in most cache implementations
        return 0
    
    def _get_ttl_for_status(self, status: str) -> int:
        """Get appropriate TTL based on status."""
        ttl_map = {
            "pending": 1800,      # 30 minutes
            "processing": 3600,   # 1 hour
            "completed": 86400,   # 24 hours
            "failed": 3600,       # 1 hour
        }
        return ttl_map.get(status, self._default_ttl)