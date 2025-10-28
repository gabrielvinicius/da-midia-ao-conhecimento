# src/admin/application/queries/admin_queries.py
from typing import Dict, Any
from uuid import UUID
class AdminQueries:
    """
    Admin queries service following SOLID principles.
    
    Single Responsibility: Handle admin-specific query operations.
    Dependency Inversion: Depends on query abstractions.
    """
    
    def __init__(self, auth_queries: AuthQueries, media_queries: MediaQueries):
        self.auth_queries = auth_queries
        self.media_queries = media_queries

    async def get_global_stats(self) -> Dict[str, Any]:
        """Aggregates statistics from multiple domains."""
        total_users = await self.auth_queries.count_all()
        total_media = await self.media_queries.count_all()
        processing_media = await self.media_queries.count_by_status(MediaStatus.PROCESSING)
        failed_media = await self.media_queries.count_by_status(MediaStatus.FAILED)
        completed_media = await self.media_queries.count_by_status(MediaStatus.COMPLETED)

        return {
            "total_users": total_users,
            "total_media": total_media,
            "processing_media": processing_media,
            "failed_media": failed_media,
            "completed_media": completed_media,
            "success_rate": (completed_media / total_media * 100) if total_media > 0 else 0
        }
    
    async def get_user_activity_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get activity statistics for a specific user."""
        user = await self.auth_queries.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        user_media = await self.media_queries.count_by_user(user_id)
        user_processing = await self.media_queries.count_by_user_and_status(user_id, MediaStatus.PROCESSING)
        user_failed = await self.media_queries.count_by_user_and_status(user_id, MediaStatus.FAILED)
        user_completed = await self.media_queries.count_by_user_and_status(user_id, MediaStatus.COMPLETED)
        
        return {
            "user_id": str(user_id),
            "email": user.email,
            "total_media": user_media,
            "processing_media": user_processing,
            "failed_media": user_failed,
            "completed_media": user_completed,
            "is_active": user.is_active
        }
    
    async def get_media_processing_stats(self) -> Dict[str, Any]:
        """Get detailed media processing statistics."""
        total = await self.media_queries.count_all()
        processing = await self.media_queries.count_by_status(MediaStatus.PROCESSING)
        failed = await self.media_queries.count_by_status(MediaStatus.FAILED)
        completed = await self.media_queries.count_by_status(MediaStatus.COMPLETED)
        uploaded = await self.media_queries.count_by_status(MediaStatus.UPLOADED)
        
        return {
            "total_media": total,
            "uploaded": uploaded,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "failure_rate": (failed / total * 100) if total > 0 else 0,
            "processing_rate": (processing / total * 100) if total > 0 else 0
        }
    
    async def get_system_health_status(self) -> Dict[str, Any]:
        """Get system health status indicators."""
        # Basic health checks
        total_failed = await self.media_queries.count_by_status(MediaStatus.FAILED)
        total_processing = await self.media_queries.count_by_status(MediaStatus.PROCESSING)
        total_users = await self.auth_queries.count_all()
        active_users = await self.auth_queries.count_active()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if total_failed > 10:  # More than 10 failed items
            health_status = "warning"
            issues.append(f"{total_failed} failed media items need attention")
        
        if total_processing > 50:  # Too many items processing
            health_status = "warning" 
            issues.append(f"{total_processing} items in processing queue")
        
        if active_users / total_users < 0.5 if total_users > 0 else False:  # Less than 50% active users
            issues.append("Low user activity detected")
        
        return {
            "status": health_status,
            "total_users": total_users,
            "active_users": active_users,
            "failed_media": total_failed,
            "processing_media": total_processing,
            "issues": issues,
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }