from uuid import uuid4

import pytest

from src.notifications.application.dtos import (
    GetUserNotificationsQuery,
    SendNotificationCommand,
)
from src.notifications.application.services.notification_read_service import (
    NotificationReadService,
)
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.domain import (
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)


class FakeRepo:
    def __init__(self):
        self.saved = {}

    async def save(self, notification: Notification) -> Notification:
        self.saved[str(notification.id)] = notification
        return notification

    async def find_by_id(self, notification_id):
        return self.saved.get(str(notification_id))

    async def list_by_user(self, user_id):
        return [n for n in self.saved.values() if str(n.user_id) == str(user_id)]

    async def delete(self, notification_id):
        return bool(self.saved.pop(str(notification_id), None))

    async def mark_as_read(self, notification_id):
        notif = self.saved.get(str(notification_id))
        if notif:
            notif.mark_as_opened()
            return True
        return False

    async def count_all(self):
        return len(self.saved)

    async def count_unread_all(self):
        return sum(1 for n in self.saved.values() if n.opened_at is None)

    async def count_by_user_id(self, user_id):
        return len(await self.list_by_user(user_id))

    async def count_unread_by_user_id(self, user_id):
        return sum(1 for n in self.saved.values() if str(n.user_id) == str(user_id) and n.opened_at is None)

    async def delete_older_than(self, days_to_keep: int) -> int:
        return 0


class FakeDelivery:
    def __init__(self):
        self.sent = []

    async def send_to_user(self, user_id, payload):
        self.sent.append((user_id, payload))
        return True


class FakeAuthQueries:
    async def get_user_by_id(self, user_id):
        return object()

    async def get_user_by_email(self, email):
        return None

    async def list_all(self, page, limit, search=None):
        return []

    async def count_filtered(self, search=None):
        return 0


class FakeLogger:
    async def log_operation(self, **kwargs):
        return None
    def info(self, *args, **kwargs):
        return None
    def warning(self, *args, **kwargs):
        return None
    def error(self, *args, **kwargs):
        return None


class FakeMetrics:
    async def record_operation(self, **kwargs):
        return None
    def set_context(self, *args, **kwargs):
        return None
    async def record_notification_sent(self, channel: str) -> None:
        return None


@pytest.mark.integration
@pytest.mark.anyio
async def test_send_notification_uses_ports_and_persists():
    repo = FakeRepo()
    read_service = NotificationReadService(notification_repo=repo)
    service = NotificationService(
        notification_repo=repo,
        delivery=FakeDelivery(),
        auth_queries=FakeAuthQueries(),
        notification_logger=FakeLogger(),
        notification_metrics=FakeMetrics(),
        notification_read_service=read_service,
    )

    cmd = SendNotificationCommand(
        user_id=uuid4(),
        message="hello",
        notification_type=NotificationType.WEBSOCKET,
        priority=NotificationPriority.NORMAL,
    )
    notif_id = await service.send_notification(cmd)

    stored = repo.saved[str(notif_id)]
    assert stored.status in {NotificationStatus.SENT, NotificationStatus.PENDING}

    notifications = await service.get_user_notifications(
        GetUserNotificationsQuery(user_id=cmd.user_id, include_read=True, limit=50)
    )
    assert len(notifications) == 1
