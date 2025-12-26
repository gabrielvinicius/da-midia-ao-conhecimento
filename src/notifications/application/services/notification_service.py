# src/notifications/application/services/notification_service.py
"""Consolidated Notification Service. This single service now handles all logic
related to notifications, including sending, delivery, and management.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.notifications.application.ports import (
    AuthQueriesPort,
    NotificationDeliveryPort,
    NotificationLoggerPort,
    NotificationMetricsPort,
    NotificationRepositoryPort,
)
from src.notifications.domain import Notification, NotificationStatus

from ..dtos import (
    CancelNotificationCommand,
    CleanupOldNotificationsCommand,
    GetNotificationQuery,
    GetNotificationStatsQuery,
    GetUserNotificationsQuery,
    MarkNotificationAsReadCommand,
    SendNotificationCommand,
)
from .notification_read_service import NotificationReadService

logger = structlog.get_logger(__name__)


class NotificationService:
    """Consolidated service for all notification operations."""

    def __init__(
        self,
        notification_repo: NotificationRepositoryPort,
        delivery: NotificationDeliveryPort,
        auth_queries: AuthQueriesPort,
        notification_logger: NotificationLoggerPort,
        notification_metrics: NotificationMetricsPort,
        notification_read_service: NotificationReadService,
        email_sender: Any = None,
        sms_sender: Any = None,
        push_sender: Any = None
    ):
        self.repo = notification_repo
        self.delivery = delivery
        self.auth_queries = auth_queries
        self.logger = notification_logger
        self.metrics = notification_metrics
        self.notification_read_service = notification_read_service
        self.email_sender = email_sender
        self.sms_sender = sms_sender
        self.push_sender = push_sender

    # --- Commands ---

    async def send_notification(
        self,
        command: SendNotificationCommand,
        *,
        final_attempt: bool = False,
    ) -> UUID:
        """Sends a notification to a user, handling creation and delivery."""
        start_time = time.monotonic()
        success = False
        error = None
        notification_id = None

        logger.info(
            "notification.send.started",
            user_id=str(command.user_id),
            type=command.notification_type.value,
        )
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
            if await self.delivery.send_to_user(
                command.user_id,
                {
                    "notification_id": str(notification_id),
                    "type": command.notification_type.value,
                    "message": command.message,
                    "priority": command.priority.value,
                    "created_at": saved_notification.created_at,
                    "variables": saved_notification.variables,
                },
            ):
                saved_notification.status = NotificationStatus.SENT
                await self.repo.save(saved_notification)
                self.logger.info(
                    "notification.delivered.websocket",
                    notification_id=str(notification_id),
                )
                await self.metrics.record_notification_sent(
                    channel=command.notification_type.value
                )

            success = True
            logger.info(
                "notification.send.completed",
                notification_id=str(notification_id),
            )
            return notification_id

        except Exception as e:
            error = e
            logger.error(
                "notification.send.failed",
                user_id=str(command.user_id),
                type=command.notification_type.value,
                error=str(e),
            )
            if notification_id:
                notification = await self.repo.find_by_id(notification_id)
                if notification:
                    if final_attempt:
                        notification.mark_as_failed(str(e))
                    else:
                        notification.record_transient_error(str(e))
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
                error=error,
            )

    async def mark_notification_as_read(
        self, command: MarkNotificationAsReadCommand
    ) -> bool:
        """Marks a notification as read."""
        notification = await self.repo.find_by_id(command.notification_id)
        if not notification or notification.user_id != command.user_id:
            return False
        notification.mark_as_opened()
        await self.repo.save(notification)
        return True

    async def cancel_notification(self, command: CancelNotificationCommand) -> bool:
        """Cancel a pending notification."""
        notification = await self.repo.find_by_id(command.notification_id)
        if not notification or notification.user_id != command.user_id:
            return False
        if notification.status in {
            NotificationStatus.SENT,
            NotificationStatus.DELIVERED,
            NotificationStatus.READ,
        }:
            return False
        notification.mark_as_failed("cancelled_by_user")
        await self.repo.save(notification)
        return True

    async def cleanup_old_notifications(
        self, command: CleanupOldNotificationsCommand
    ) -> int:
        """Clean up old notifications."""
        deleted = await self.repo.delete_older_than(command.days_to_keep)
        self.logger.info(
            "notification.cleanup.completed",
            deleted=deleted,
            days_to_keep=command.days_to_keep,
        )
        return deleted

    # --- Queries (Delegated to Read Service) ---

    async def get_notification_by_id(
        self, query: GetNotificationQuery
    ) -> Optional[Notification]:
        """Retrieves a notification by its unique ID."""
        return await self.notification_read_service.get_notification_by_id(query)

    async def get_user_notifications(
        self,
        query: GetUserNotificationsQuery,
    ) -> List[Notification]:
        """Retrieves notifications for a user."""
        return await self.notification_read_service.get_user_notifications(query)

    async def get_notification_stats(
        self, query: GetNotificationStatsQuery
    ) -> Dict[str, Any]:
        """Get notification statistics."""
        return await self.notification_read_service.get_notification_stats(query)
