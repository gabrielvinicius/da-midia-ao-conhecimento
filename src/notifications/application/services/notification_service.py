"""
Notification Service - Single Responsibility: Core notification operations
Follows SRP by handling only core notification management.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog

from src.notifications.domain.interfaces import (
    INotificationService, INotificationRepository, INotificationDeliveryService,
    INotificationPreferences, INotificationQueue
)
from src.notifications.domain.notification import (
    Notification, NotificationType, NotificationStatus, NotificationPriority
)

logger = structlog.get_logger(__name__)


class NotificationService(INotificationService):
    """
    Core notification service following SOLID principles.
    
    Single Responsibility: Handle core notification operations.
    Open/Closed: Extensible through delivery services and channels.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        notification_repository: INotificationRepository,
        delivery_service: INotificationDeliveryService,
        preferences_service: INotificationPreferences,
        queue_service: INotificationQueue
    ):
        self.notification_repository = notification_repository
        self.delivery_service = delivery_service
        self.preferences_service = preferences_service
        self.queue_service = queue_service
    
    async def send_notification(
        self,
        user_id: UUID,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Send a notification to a user.
        
        Args:
            user_id: Target user ID
            message: Notification message
            notification_type: Type of notification
            priority: Notification priority
            template: Template name (optional)
            variables: Template variables (optional)
            
        Returns:
            UUID: Notification ID
        """
        try:
            # Create notification entity
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                content=message,
                priority=priority,
                template_name=template,
                variables=variables or {},
                status=NotificationStatus.PENDING
            )
            
            # Save notification
            saved_notification = await self.notification_repository.save(notification)
            
            # Add to queue for processing
            await self.queue_service.enqueue(saved_notification, priority)
            
            logger.info(
                "notification.created",
                notification_id=str(saved_notification.id),
                user_id=str(user_id),
                type=notification_type.value,
                priority=priority.value
            )
            
            return saved_notification.id
            
        except Exception as e:
            logger.error(
                "notification.creation_failed",
                user_id=str(user_id),
                type=notification_type.value,
                error=str(e)
            )
            raise
    
    async def send_bulk_notification(
        self,
        user_ids: List[UUID],
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> List[UUID]:
        """
        Send notifications to multiple users.
        
        Args:
            user_ids: List of target user IDs
            message: Notification message
            notification_type: Type of notification
            priority: Notification priority
            
        Returns:
            List[UUID]: List of notification IDs
        """
        notification_ids = []
        failed_count = 0
        
        for user_id in user_ids:
            try:
                notification_id = await self.send_notification(
                    user_id, message, notification_type, priority
                )
                notification_ids.append(notification_id)
            except Exception as e:
                failed_count += 1
                logger.warning(
                    "notification.bulk_send_failed",
                    user_id=str(user_id),
                    error=str(e)
                )
        
        logger.info(
            "notification.bulk_send_completed",
            total_users=len(user_ids),
            successful=len(notification_ids),
            failed=failed_count
        )
        
        return notification_ids
    
    async def retry_failed_notification(self, notification_id: UUID) -> bool:
        """
        Retry a failed notification.
        
        Args:
            notification_id: ID of the notification to retry
            
        Returns:
            bool: True if retry was successful
        """
        try:
            notification = await self.notification_repository.find_by_id(notification_id)
            if not notification:
                logger.warning("notification.retry_not_found", notification_id=str(notification_id))
                return False
            
            if not notification.can_retry():
                logger.warning(
                    "notification.retry_not_allowed",
                    notification_id=str(notification_id),
                    retries=notification.retries,
                    max_retries=notification.max_retries
                )
                return False
            
            # Reset status and add back to queue
            notification.status = NotificationStatus.PENDING
            notification.error_message = None
            await self.notification_repository.save(notification)
            
            # Re-queue with delay
            await self.queue_service.requeue(notification_id, delay_seconds=300)
            
            logger.info(
                "notification.retry_queued",
                notification_id=str(notification_id),
                retry_count=notification.retries + 1
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "notification.retry_failed",
                notification_id=str(notification_id),
                error=str(e)
            )
            return False
    
    async def get_user_notifications(
        self, 
        user_id: UUID, 
        include_read: bool = True,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            include_read: Whether to include read notifications
            limit: Maximum number of notifications to return
            
        Returns:
            List[Notification]: User's notifications
        """
        try:
            notifications = await self.notification_repository.find_by_user_id(user_id, limit)
            
            if not include_read:
                # Filter out notifications that have been opened
                notifications = [n for n in notifications if not n.opened_at]
            
            logger.debug(
                "notification.user_notifications_retrieved",
                user_id=str(user_id),
                count=len(notifications),
                include_read=include_read
            )
            
            return notifications
            
        except Exception as e:
            logger.error(
                "notification.user_notifications_failed",
                user_id=str(user_id),
                error=str(e)
            )
            return []
    
    async def mark_notification_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for authorization)
            
        Returns:
            bool: True if successful
        """
        try:
            notification = await self.notification_repository.find_by_id(notification_id)
            if not notification:
                return False
            
            # Check authorization
            if notification.user_id != user_id:
                logger.warning(
                    "notification.unauthorized_read_attempt",
                    notification_id=str(notification_id),
                    user_id=str(user_id)
                )
                return False
            
            # Mark as opened
            notification.mark_as_opened()
            await self.notification_repository.save(notification)
            
            logger.info(
                "notification.marked_as_read",
                notification_id=str(notification_id),
                user_id=str(user_id)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "notification.mark_read_failed",
                notification_id=str(notification_id),
                error=str(e)
            )
            return False
    
    async def get_notification_stats(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get notification statistics.
        
        Args:
            user_id: Optional user ID for user-specific stats
            
        Returns:
            Dict with notification statistics
        """
        try:
            if user_id:
                # User-specific stats
                notifications = await self.notification_repository.find_by_user_id(user_id, limit=1000)
                total = len(notifications)
                unread = len([n for n in notifications if not n.opened_at])
                failed = len([n for n in notifications if n.status == NotificationStatus.FAILED])
                
                stats = {
                    "user_id": str(user_id),
                    "total_notifications": total,
                    "unread_notifications": unread,
                    "failed_notifications": failed,
                    "read_rate": ((total - unread) / total * 100) if total > 0 else 0
                }
            else:
                # System-wide stats
                pending_notifications = await self.notification_repository.find_by_status(NotificationStatus.PENDING)
                failed_notifications = await self.notification_repository.find_by_status(NotificationStatus.FAILED)
                queue_size = await self.queue_service.get_queue_size()
                
                stats = {
                    "pending_notifications": len(pending_notifications),
                    "failed_notifications": len(failed_notifications),
                    "queue_size": queue_size,
                    "system_health": "healthy" if len(failed_notifications) < 10 else "degraded"
                }
            
            logger.debug("notification.stats_retrieved", stats=stats)
            return stats
            
        except Exception as e:
            logger.error("notification.stats_failed", error=str(e))
            return {"error": str(e)}
    
    async def cancel_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """
        Cancel a pending notification.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for authorization)
            
        Returns:
            bool: True if successful
        """
        try:
            notification = await self.notification_repository.find_by_id(notification_id)
            if not notification:
                return False
            
            # Check authorization
            if notification.user_id != user_id:
                logger.warning(
                    "notification.unauthorized_cancel_attempt",
                    notification_id=str(notification_id),
                    user_id=str(user_id)
                )
                return False
            
            # Only allow cancellation of pending notifications
            if notification.status not in [NotificationStatus.PENDING, NotificationStatus.QUEUED]:
                logger.warning(
                    "notification.cancel_not_allowed",
                    notification_id=str(notification_id),
                    status=notification.status.value
                )
                return False
            
            # Cancel notification
            notification.status = NotificationStatus.CANCELLED
            await self.notification_repository.save(notification)
            
            logger.info(
                "notification.cancelled",
                notification_id=str(notification_id),
                user_id=str(user_id)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "notification.cancel_failed",
                notification_id=str(notification_id),
                error=str(e)
            )
            return False
    
    async def cleanup_old_notifications(self, days_to_keep: int = 30) -> int:
        """
        Clean up old notifications.
        
        Args:
            days_to_keep: Number of days to keep notifications
            
        Returns:
            int: Number of notifications cleaned up
        """
        try:
            # This would be implemented with a more sophisticated cleanup strategy
            # For now, return 0 as placeholder
            cleaned_count = 0
            
            logger.info(
                "notification.cleanup_completed",
                days_to_keep=days_to_keep,
                cleaned_count=cleaned_count
            )
            
            return cleaned_count
            
        except Exception as e:
            logger.error("notification.cleanup_failed", error=str(e))
            return 0