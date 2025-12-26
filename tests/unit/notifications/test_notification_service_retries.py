import pytest
from uuid import uuid4

from src.notifications.application.dtos import SendNotificationCommand
from src.notifications.application.services.notification_service import NotificationService
from src.notifications.domain import (
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from src.notifications.application.ports import (
    NotificationRepositoryPort,
    NotificationDeliveryPort,
    AuthQueriesPort,
    NotificationLoggerPort,
    NotificationMetricsPort,
)


class FakeRepo(NotificationRepositoryPort):
    def __init__(self):
        self.saved = {}

    async def save(self, notification: Notification):
        self.saved[str(notification.id)] = notification
        return notification

    async def find_by_id(self, notification_id):
        return self.saved.get(str(notification_id))

    async def list_for_user(self, user_id, limit=50, offset=0):
        return []

    async def delete_older_than(self, days_to_keep: int):
        return 0

    async def mark_as_read(self, notification_id):
        return False

    async def get_stats(self):
        return {}


class FailingDelivery(NotificationDeliveryPort):
    async def send_to_user(self, user_id, payload):
        raise RuntimeError("entrega falhou")


class NoOpAuth(AuthQueriesPort):
    async def get_user(self, user_id):
        return None


class NoOpLogger(NotificationLoggerPort):
    async def log_operation(self, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class NoOpMetrics(NotificationMetricsPort):
    async def record_notification_sent(self, channel: str):
        return None


class DummyReadService:
    async def get_notification_by_id(self, query):
        return None

    async def get_user_notifications(self, query):
        return []

    async def get_notification_stats(self, query):
        return {}


@pytest.mark.asyncio
async def test_notification_failure_intermediate_keeps_status_pending():
    repo = FakeRepo()
    service = NotificationService(
        notification_repo=repo,
        delivery=FailingDelivery(),
        auth_queries=NoOpAuth(),
        notification_logger=NoOpLogger(),
        notification_metrics=NoOpMetrics(),
        notification_read_service=DummyReadService(),
    )

    cmd = SendNotificationCommand(
        user_id=uuid4(),
        message="teste",
        notification_type=NotificationType.WEBSOCKET,
        priority=NotificationPriority.NORMAL,
    )

    with pytest.raises(RuntimeError):
        await service.send_notification(cmd, final_attempt=False)

    saved = list(repo.saved.values())[0]
    assert saved.status == NotificationStatus.PENDING
    assert saved.retries == 1  # erro transitório registra retry


@pytest.mark.asyncio
async def test_notification_failure_final_marks_failed():
    repo = FakeRepo()
    service = NotificationService(
        notification_repo=repo,
        delivery=FailingDelivery(),
        auth_queries=NoOpAuth(),
        notification_logger=NoOpLogger(),
        notification_metrics=NoOpMetrics(),
        notification_read_service=DummyReadService(),
    )

    cmd = SendNotificationCommand(
        user_id=uuid4(),
        message="teste",
        notification_type=NotificationType.WEBSOCKET,
        priority=NotificationPriority.NORMAL,
    )

    with pytest.raises(RuntimeError):
        await service.send_notification(cmd, final_attempt=True)

    saved = list(repo.saved.values())[0]
    assert saved.status == NotificationStatus.FAILED
    assert saved.retries == 1
