import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from src.notifications.domain.notification import (
    Notification, 
    NotificationType, 
    NotificationStatus, 
    NotificationPriority
)
from src.shared.utils.time_utils import utcnow

class TestNotificationDomain:
    def test_create_notification(self):
        user_id = uuid4()
        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL,
            content="Hello World"
        )
        
        assert notification.id is not None
        assert notification.status == NotificationStatus.PENDING
        assert notification.created_at is not None

    def test_mark_as_sent(self):
        notification = Notification(
            user_id=uuid4(),
            type=NotificationType.SMS,
            content="Test"
        )
        assert notification.sent_at is None
        
        notification.mark_as_sent()
        
        assert notification.status == NotificationStatus.SENT
        assert notification.sent_at is not None

    def test_mark_as_failed_increments_retries(self):
        notification = Notification(
            user_id=uuid4(),
            type=NotificationType.PUSH,
            content="Test",
            max_retries=3
        )
        
        notification.mark_as_failed("Connection error")
        
        assert notification.status == NotificationStatus.FAILED
        assert notification.error_message == "Connection error"
        assert notification.retries == 1

    def test_can_retry(self):
        notification = Notification(
            user_id=uuid4(),
            type=NotificationType.PUSH,
            content="Test",
            max_retries=2,
            retries=0
        )
        
        # Not failed yet
        assert not notification.can_retry()
        
        notification.mark_as_failed("Error 1")
        assert notification.can_retry() # retries=1, max=2
        
        notification.mark_as_failed("Error 2") # retries=2, max=2
        assert not notification.can_retry()

    def test_is_expired(self):
        user_id = uuid4()
        # Mock created_at to be 25 hours ago
        past_time = utcnow() - timedelta(hours=25)
        
        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL,
            content="Old news",
            created_at=past_time
        )
        
        assert notification.is_expired(expiry_hours=24) is True
        assert notification.is_expired(expiry_hours=26) is False
