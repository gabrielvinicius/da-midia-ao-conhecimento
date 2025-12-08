# src/notifications/application/services/notification_service.py
"""Consolidated Notification Service. This single service now handles all logic
related to notifications, including sending, delivery, and management.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.notifications.application.commands.dto import (
    CancelNotificationCommand,
    CleanupOldNotificationsCommand,
    MarkNotificationAsReadCommand,
    SendNotificationCommand,
)
from src.notifications.application.queries.dto import (
    GetNotificationQuery,
    GetNotificationStatsQuery,
    GetUserNotificationsQuery,
)
from src.notifications.domain.notification import (
    Notification,
    NotificationStatus,
)
from src.notifications.infrastructure.connection_manager import ConnectionManager
from src.notifications.infrastructure.logging import StructuredNotificationLogger
from src.notifications.infrastructure.notification_repository import (
    NotificationRepository,
)
from src.notifications.application.notification_read_service import NotificationReadService # New import
from src.user_management.application.auth_queries import AuthQueries

logger = structlog.get_logger(__name__)


class NotificationService:
    """Consolidated service for all notification operations.
    
    Combines logic previously split between commands and queries.
    """

    def __init__(
        self,
        notification_repo: NotificationRepository,
        connection_manager: ConnectionManager,
        auth_queries: AuthQueries,
        notification_logger: StructuredNotificationLogger,
        notification_metrics: PrometheusNotificationMetrics,
        notification_read_service: NotificationReadService, # New dependency
        email_sender: Any = None, # Placeholder
        sms_sender: Any = None,   # Placeholder
        push_sender: Any = None   # Placeholder
    ):
        self.repo = notification_repo
        self.connection_manager = connection_manager
        self.auth_queries = auth_queries
        self.logger = notification_logger
        self.metrics = notification_metrics
        self.notification_read_service = notification_read_service # Assign new dependency
        self.email_sender = email_sender
        self.sms_sender = sms_sender
        self.push_sender = push_sender

    # --- Commands ---

    async def send_notification(
        self,
        command: SendNotificationCommand,
    ) -> UUID:
        """Sends a notification to a user, handling creation and delivery."""
        start_time = time.monotonic()
        success = False
        error = None
        notification_id = None

        logger.info("notification.send.started", user_id=str(command.user_id), type=command.notification_type.value)
        try:
            # 1. Create notification entity
            notification = Notification(
                user_id=command.user_id,
                type=command.notification_type,
                content=command.message,
                priority=command.priority,
                template_name=command.template,
                variables=command.variables or {},
                status=NotificationStatus.PENDING
            )
            saved_notification = await self.repo.save(notification)
            notification_id = saved_notification.id

            # 2. Attempt delivery (WebSocket, Email, SMS, Push)
            # WebSocket delivery
            if await self.connection_manager.send_to_user(command.user_id, {"type": command.notification_type.value, "message": command.message}):
                saved_notification.status = NotificationStatus.SENT
                await self.repo.save(saved_notification)
                logger.info("notification.delivered.websocket", notification_id=str(notification_id))

            success = True
            logger.info("notification.send.completed", notification_id=str(notification_id))
            return notification_id

        except Exception as e:
            error = e
            logger.error("notification.send.failed", user_id=str(command.user_id), type=command.notification_type.value, error=str(e))
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
                user_id=str(command.user_id),
                notification_id=str(notification_id) if notification_id else "N/A",
                type=command.notification_type.value,
                success=success,
                duration=duration,
                error=error
            )

    async def mark_notification_as_read(self, command: MarkNotificationAsReadCommand) -> bool:
        """Marks a notification as read."""
        notification = await self.repo.find_by_id(command.notification_id)
        if not notification or notification.user_id != command.user_id:
            return False
        notification.mark_as_opened()
        await self.repo.save(notification)
        return True

    async def cancel_notification(self, command: CancelNotificationCommand) -> bool:
        """Cancel a pending notification."""
        # Placeholder for actual cancel logic
        return False

    async def cleanup_old_notifications(self, command: CleanupOldNotificationsCommand) -> int:
        """Clean up old notifications."""
        # Placeholder for actual cleanup logic
        return 0

    # --- Queries (Delegated to Read Service) ---

    async def get_notification_by_id(self, query: GetNotificationQuery) -> Optional[Notification]:
        """Retrieves a notification by its unique ID."""
        return await self.notification_read_service.get_notification_by_id(query)

    async def get_user_notifications(
        self,
        query: GetUserNotificationsQuery,
    ) -> List[Notification]:
        """Retrieves notifications for a user."""
        return await self.notification_read_service.get_user_notifications(query)

    async def get_notification_stats(self, query: GetNotificationStatsQuery) -> Dict[str, Any]:
        """Get notification statistics."""
        return await self.notification_read_service.get_notification_stats(query)
