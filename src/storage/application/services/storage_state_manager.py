"""
Storage State Manager - Single Responsibility: State management.
Follows SRP by handling only state tracking concerns for storage operations.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
import structlog

from src.storage.domain.interfaces import IStorageStateManager
from src.shared.domain.interfaces import CacheService

logger = structlog.get_logger(__name__)


class StorageStateManager(IStorageStateManager):
    """
    Storage state manager following SRP.
    Single responsibility: Track and manage file operation states.
    """
    
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service
        self._state_prefix = "storage_state"
        self._default_ttl = 3600  # 1 hour
    
    async def update_file_status(
        self, 
        file_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update file operation status."""
        state_data = {
            "file_id": str(file_id),
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        cache_key = f"{self._state_prefix}:{file_id}"
        ttl = self._get_ttl_for_status(status)
        
        await self._cache.set(cache_key, state_data, ttl)
        
        logger.info(
            "storage.state.updated",
            file_id=str(file_id),
            status=status,
            error_message=error_message
        )
    
    async def get_file_status(self, file_id: UUID) -> Optional[str]:
        """Get current file operation status."""
        cache_key = f"{self._state_prefix}:{file_id}"
        state_data = await self._cache.get(cache_key)
        
        if state_data:
            return state_data.get("status")
        return None
    
    async def cleanup_old_states(self, days_to_keep: int = 7) -> int:
        """Clean up old file operation states."""
        # TTL-based cleanup is automatic in most cache implementations
        logger.info(
            "storage.state.cleanup_completed",
            days_to_keep=days_to_keep,
            cleaned_count=0
        )
        return 0
    
    def _get_ttl_for_status(self, status: str) -> int:
        """Get appropriate TTL based on status."""
        ttl_map = {
            "uploading": 1800,    # 30 minutes
            "processing": 3600,   # 1 hour
            "completed": 86400,   # 24 hours
            "failed": 7200,       # 2 hours
            "deleted": 3600       # 1 hour
        }
        return ttl_map.get(status, self._default_ttl)