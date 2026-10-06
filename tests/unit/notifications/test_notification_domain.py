from uuid import uuid4

from src.notifications.domain import Notification, NotificationStatus, NotificationType


def test_a_new_notice_waits_to_be_sent_over_the_websocket():
    notification = Notification(user_id=uuid4(), content="Transcrição concluída.")

    assert notification.status == NotificationStatus.PENDING
    assert notification.type == NotificationType.WEBSOCKET
    assert notification.created_at == notification.updated_at


def test_sent_then_read():
    notification = Notification(user_id=uuid4(), content="Análise concluída.")

    notification.mark_as_sent()
    assert notification.status == NotificationStatus.SENT and notification.sent_at is not None

    notification.mark_as_opened()
    assert notification.status == NotificationStatus.READ
    assert notification.opened_at == notification.updated_at
