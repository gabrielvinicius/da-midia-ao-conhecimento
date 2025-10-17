# src/notifications/application/notification_service.py
from typing import List
from uuid import UUID
import structlog

from src.notifications.domain.interfaces import INotificationRepository
from src.notifications.domain.notification import Notification, NotificationStatus

logger = structlog.get_logger(__name__)


class LegacyNotificationService:
    """
    Legacy notification service - maintained for backward compatibility.
    
    For new code, use the new NotificationService in services/notification_service.py
    """
    
    def __init__(self, notification_repository: INotificationRepository):
        self.notification_repository = notification_repository

    async def get_notifications_for_user(self, user_id: str) -> List[Notification]:
        """
        Retrieves all notifications for a given user.
        
        Legacy method - use new NotificationService.get_user_notifications() for new code.
        """
        try:
            user_uuid = UUID(user_id)
            notifications = await self.notification_repository.find_by_user_id(user_uuid)
            
            logger.debug(
                "legacy.notifications_retrieved",
                user_id=user_id,
                count=len(notifications)
            )
            
            return notifications
            
        except ValueError:
            logger.error("legacy.invalid_user_id", user_id=user_id)
            return []
        except Exception as e:
            logger.error(
                "legacy.get_notifications_failed",
                user_id=user_id,
                error=str(e)
            )
            return []

    async def mark_notification_as_read(self, notification_id: str) -> None:
        """
        Marks a notification as read/acknowledged.
        
        Legacy method - use new NotificationService.mark_notification_as_read() for new code.
        """
        try:
            notification_uuid = UUID(notification_id)
            
            # Update notification status
            await self.notification_repository.update_status(
                notification_uuid, 
                NotificationStatus.SENT  # Mark as sent (legacy behavior)
            )
            
            logger.info(
                "legacy.notification_marked_read",
                notification_id=notification_id
            )
            
        except ValueError:
            logger.error("legacy.invalid_notification_id", notification_id=notification_id)
        except Exception as e:
            logger.error(
                "legacy.mark_read_failed",
                notification_id=notification_id,
                error=str(e)
            )