"""
Domain interfaces for admin module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID
from src.auth.domain.user import User
from src.media_management.domain.media import Media, MediaStatus


class IAdminQueries(ABC):
    """Interface for admin query operations."""
    
    @abstractmethod
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        pass
    
    @abstractmethod
    async def get_user_activity_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get activity statistics for a specific user."""
        pass
    
    @abstractmethod
    async def get_media_processing_stats(self) -> Dict[str, Any]:
        """Get media processing statistics."""
        pass
    
    @abstractmethod
    async def get_system_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        pass


class IAdminUserService(ABC):
    """Interface for admin user management operations."""
    
    @abstractmethod
    async def update_user_role(self, user_id: UUID, new_role: str, admin_user: User) -> User:
        """Update user role with admin validation."""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
        """Delete user with admin validation."""
        pass
    
    @abstractmethod
    async def activate_user(self, user_id: UUID, admin_user: User) -> User:
        """Activate user account."""
        pass
    
    @abstractmethod
    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User:
        """Deactivate user account."""
        pass
    
    @abstractmethod
    async def bulk_update_users(self, user_updates: List[Dict], admin_user: User) -> List[User]:
        """Update multiple users in bulk."""
        pass


class IAdminMediaService(ABC):
    """Interface for admin media management operations."""
    
    @abstractmethod
    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        """Delete media with admin validation."""
        pass
    
    @abstractmethod
    async def reprocess_media(self, media_id: UUID, admin_user: User) -> None:
        """Reprocess failed media."""
        pass
    
    @abstractmethod
    async def bulk_reprocess_failed_media(self, admin_user: User) -> int:
        """Reprocess all failed media items."""
        pass
    
    @abstractmethod
    async def cleanup_orphaned_files(self, admin_user: User) -> int:
        """Clean up orphaned files in storage."""
        pass
    
    @abstractmethod
    async def get_media_by_status(self, status: MediaStatus) -> List[Media]:
        """Get media items by processing status."""
        pass


class IAdminAuditService(ABC):
    """Interface for admin audit and logging operations."""
    
    @abstractmethod
    async def log_admin_action(
        self, 
        admin_user: User, 
        action: str, 
        target_type: str, 
        target_id: UUID, 
        details: Optional[Dict] = None
    ) -> None:
        """Log administrative action for audit trail."""
        pass
    
    @abstractmethod
    async def get_audit_log(
        self, 
        page: int = 1, 
        limit: int = 50,
        admin_id: Optional[UUID] = None,
        action_type: Optional[str] = None
    ) -> List[Dict]:
        """Get audit log entries."""
        pass
    
    @abstractmethod
    async def get_user_audit_trail(self, user_id: UUID) -> List[Dict]:
        """Get audit trail for specific user."""
        pass


class IAdminSystemService(ABC):
    """Interface for admin system management operations."""
    
    @abstractmethod
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics."""
        pass
    
    @abstractmethod
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        pass
    
    @abstractmethod
    async def clear_system_cache(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """Clear system caches."""
        pass
    
    @abstractmethod
    async def backup_database(self, admin_user: User) -> str:
        """Initiate database backup."""
        pass
    
    @abstractmethod
    async def maintenance_mode(self, enabled: bool, admin_user: User) -> None:
        """Enable/disable maintenance mode."""
        pass


class IAdminNotificationService(ABC):
    """Interface for admin notification operations."""
    
    @abstractmethod
    async def send_system_notification(
        self, 
        message: str, 
        severity: str,
        admin_user: User,
        target_users: Optional[List[UUID]] = None
    ) -> None:
        """Send system-wide notification."""
        pass
    
    @abstractmethod
    async def notify_user_action(
        self,
        target_user_id: UUID,
        action: str,
        admin_user: User,
        details: Optional[str] = None
    ) -> None:
        """Notify user about admin action."""
        pass
    
    @abstractmethod
    async def get_notification_history(
        self,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict]:
        """Get notification history."""
        pass