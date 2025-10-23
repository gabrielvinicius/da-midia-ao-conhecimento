# src/notifications/application/services/notification_service.py
"""
Consolidated Notification Service. This single service now handles all logic
related to notifications, including sending, delivery, and management.
"""
import structlog
from typing import Dict, Any, List, Optional
from uuid import UUID
import time

from src.notifications.domain.notification import Notification, NotificationStatus, NotificationType, NotificationPriority
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.notifications.infrastructure.connection_manager import ConnectionManager
from src.notifications.infrastructure.logging import StructuredNotificationLogger
from src.notifications.infrastructure.metrics import PrometheusNotificationMetrics
from src.auth.application.queries.auth_queries import AuthQueries
from src.shared.events.event_bus import EventBus

logger = structlog.get_logger(__name__)


class NotificationService:
    """
    Consolidated service for all notification operations.
    """
    
    def __init__(
        self,
        notification_repo: NotificationRepository,
        connection_manager: ConnectionManager,
        auth_queries: AuthQueries,
        event_bus: EventBus,
        notification_logger: StructuredNotificationLogger,
        notification_metrics: PrometheusNotificationMetrics,
        email_sender: Any = None, # Placeholder
        sms_sender: Any = None,   # Placeholder
        push_sender: Any = None   # Placeholder
    ):
        self.repo = notification_repo
        self.connection_manager = connection_manager
        self.auth_queries = auth_queries
        self.event_bus = event_bus
        self.logger = notification_logger
        self.metrics = notification_metrics
        self.email_sender = email_sender
        self.sms_sender = sms_sender
        self.push_sender = push_sender

    async def send_notification(
        self,
        user_id: UUID,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Sends a notification to a user, handling creation and delivery."""
        start_time = time.monotonic()
        success = False
        error = None
        notification_id = None

        logger.info("notification.send.started", user_id=str(user_id), type=notification_type.value)
        try:
            # 1. Create notification entity
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                content=message,
                priority=priority,
                template_name=template,
                variables=variables or {},
                status=NotificationStatus.PENDING
            )
            saved_notification = await self.repo.save(notification)
            notification_id = saved_notification.id

            # 2. Attempt delivery (WebSocket, Email, SMS, Push)
            # WebSocket delivery
            if await self.connection_manager.send_to_user(user_id, {"type": notification_type.value, "message": message}):
                saved_notification.status = NotificationStatus.SENT
                await self.repo.save(saved_notification)
                logger.info("notification.delivered.websocket", notification_id=str(notification_id))
            
            # Placeholder for other delivery channels
            # if self.email_sender: await self.email_sender.send(user_id, message, template, variables)
            # if self.sms_sender: await self.sms_sender.send(user_id, message)
            # if self.push_sender: await self.push_sender.send(user_id, message)

            success = True
            logger.info("notification.send.completed", notification_id=str(notification_id))
            return notification_id

        except Exception as e:
            error = e
            logger.error("notification.send.failed", user_id=str(user_id), type=notification_type.value, error=str(e))
            if notification_id:
                notification = await self.repo.get_by_id(notification_id)
                if notification:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = str(e)
                    await self.repo.save(notification)
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.logger.log_operation(
                operation="send_notification",
                user_id=str(user_id),
                notification_id=str(notification_id) if notification_id else "N/A",
                type=notification_type.value,
                success=success,
                duration=duration,
                error=error
            )
            # Metrics recording can be added here

    async def get_user_notifications(
        self, 
        user_id: UUID, 
        include_read: bool = True,
        limit: int = 50
    ) -> List[Notification]:
        """Retrieves notifications for a user."""
        notifications = await self.repo.find_by_user_id(user_id, limit)
        if not include_read:
            notifications = [n for n in notifications if not n.opened_at]
        return notifications

    async def mark_notification_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Marks a notification as read."""
        notification = await self.repo.find_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            return False
        notification.mark_as_opened()
        await self.repo.save(notification)
        return True

    async def get_notification_stats(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get notification statistics."""
        # Placeholder for actual stats logic
        return {"total": 0, "unread": 0}

    async def cancel_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """Cancel a pending notification."""
        # Placeholder for actual cancel logic
        return False

    async def cleanup_old_notifications(self, days_to_keep: int = 30) -> int:
        """Clean up old notifications."""
        # Placeholder for actual cleanup logic
        return 0
