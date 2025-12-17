from typing import Any, Dict, List, Optional

from src.notifications.application.ports import NotificationRepositoryPort
from src.notifications.domain import Notification

from ..dtos import (
    GetNotificationQuery,
    GetNotificationStatsQuery,
    GetUserNotificationsQuery,
)


class NotificationReadService:
    """Read-side service for Notifications (CQRS consulta)."""

    def __init__(self, notification_repo: NotificationRepositoryPort) -> None:
        self.repo = notification_repo

    async def get_notification_by_id(
        self, query: GetNotificationQuery
    ) -> Optional[Notification]:
        """Retrieves a notification by its unique ID."""
        return await self.repo.find_by_id(query.notification_id)

    async def get_user_notifications(
        self,
        query: GetUserNotificationsQuery,
    ) -> List[Notification]:
        """Retrieves notifications for a user."""
        notifications = await self.repo.list_by_user(str(query.user_id))
        if not query.include_read:
            notifications = [n for n in notifications if not n.opened_at]
        return notifications

    async def get_notification_stats(
        self, query: GetNotificationStatsQuery
    ) -> Dict[str, Any]:
        """Get notification statistics."""
        if query.user_id:
            total = await self.repo.count_by_user_id(query.user_id)
            unread = await self.repo.count_unread_by_user_id(query.user_id)
        else:
            total = await self.repo.count_all()
            unread = await self.repo.count_unread_all()

        return {"total": total, "unread": unread}
