from typing import Any, Dict, List, Optional
from uuid import UUID

from src.notifications.application.queries.dto import (
    GetNotificationQuery,
    GetNotificationStatsQuery,
    GetUserNotificationsQuery,
)
from src.notifications.domain.notification import Notification
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.shared.utils.time_utils import utcnow


class NotificationReadService:
    """Read-side service for Notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self.repo = notification_repo

    async def get_notification_by_id(self, query: GetNotificationQuery) -> Optional[Notification]:
        """Retrieves a notification by its unique ID."""
        return await self.repo.find_by_id(query.notification_id)

    async def get_user_notifications(
        self,
        query: GetUserNotificationsQuery,
    ) -> List[Notification]:
        """Retrieves notifications for a user."""
        notifications = await self.repo.find_by_user_id(query.user_id, query.limit)
        if not query.include_read:
            notifications = [n for n in notifications if not n.opened_at]
        return notifications

    async def get_notification_stats(self, query: GetNotificationStatsQuery) -> Dict[str, Any]:
        """Get notification statistics."""
        # This logic needs to be implemented by calling repository methods
        # For now, placeholder based on original service logic
        if query.user_id:
            total = await self.repo.count_by_user_id(query.user_id)
            unread = await self.repo.count_unread_by_user_id(query.user_id)
        else:
            total = await self.repo.count_all()
            unread = await self.repo.count_unread_all()
        
        return {"total": total, "unread": unread}
