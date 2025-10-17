"""
Domain interfaces for notifications module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from uuid import UUID
from enum import Enum
from datetime import datetime
from fastapi import WebSocket

from .notification import Notification, NotificationType, NotificationStatus


class DeliveryChannel(Enum):
    """Delivery channels for notifications."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationTemplate(Enum):
    """Predefined notification templates."""
    WELCOME = "welcome"
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_FAILED = "processing_failed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SECURITY_ALERT = "security_alert"
    SYSTEM_MAINTENANCE = "system_maintenance"


class INotificationRepository(ABC):
    """Interface for notification repository operations."""
    
    @abstractmethod
    async def save(self, notification: Notification) -> Notification:
        """Save or update a notification."""
        pass
    
    @abstractmethod
    async def find_by_id(self, notification_id: UUID) -> Optional[Notification]:
        """Find notification by ID."""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID, limit: int = 50) -> List[Notification]:
        """Find notifications for a specific user."""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: NotificationStatus) -> List[Notification]:
        """Find notifications by status."""
        pass
    
    @abstractmethod
    async def update_status(self, notification_id: UUID, status: NotificationStatus, error_message: Optional[str] = None) -> None:
        """Update notification status."""
        pass
    
    @abstractmethod
    async def delete(self, notification_id: UUID) -> bool:
        """Delete a notification."""
        pass


class INotificationSender(ABC):
    """Interface for notification sending operations."""
    
    @abstractmethod
    async def send(self, notification: Notification, contact_info: Dict[str, Any]) -> bool:
        """Send a notification through specific channel."""
        pass
    
    @abstractmethod
    def supports_channel(self, channel: DeliveryChannel) -> bool:
        """Check if sender supports specific delivery channel."""
        pass
    
    @abstractmethod
    async def validate_contact_info(self, contact_info: Dict[str, Any]) -> bool:
        """Validate contact information for the channel."""
        pass


class IEmailSender(INotificationSender):
    """Interface for email notification sending."""
    
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email notification."""
        pass
    
    @abstractmethod
    async def send_template_email(self, to: str, template: NotificationTemplate, variables: Dict[str, Any]) -> bool:
        """Send templated email notification."""
        pass


class ISMSSender(INotificationSender):
    """Interface for SMS notification sending."""
    
    @abstractmethod
    async def send_sms(self, to: str, message: str) -> bool:
        """Send SMS notification."""
        pass
    
    @abstractmethod
    async def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format."""
        pass


class IWebSocketManager(ABC):
    """Interface for WebSocket connection management."""
    
    @abstractmethod
    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Accept and register WebSocket connection."""
        pass
    
    @abstractmethod
    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Remove WebSocket connection."""
        pass
    
    @abstractmethod
    async def send_to_user(self, user_id: UUID, message: Dict[str, Any]) -> bool:
        """Send message to specific user."""
        pass
    
    @abstractmethod
    async def broadcast(self, message: Dict[str, Any], filter_criteria: Optional[Dict] = None) -> int:
        """Broadcast message to all or filtered connections."""
        pass
    
    @abstractmethod
    def get_active_connections(self, user_id: Optional[UUID] = None) -> int:
        """Get count of active connections."""
        pass


class INotificationService(ABC):
    """Interface for notification service operations."""
    
    @abstractmethod
    async def send_notification(
        self,
        user_id: UUID,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template: Optional[NotificationTemplate] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Send a notification to a user."""
        pass
    
    @abstractmethod
    async def send_bulk_notification(
        self,
        user_ids: List[UUID],
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> List[UUID]:
        """Send notifications to multiple users."""
        pass
    
    @abstractmethod
    async def retry_failed_notification(self, notification_id: UUID) -> bool:
        """Retry a failed notification."""
        pass
    
    @abstractmethod
    async def get_user_notifications(self, user_id: UUID, include_read: bool = True) -> List[Notification]:
        """Get notifications for a user."""
        pass


class INotificationTemplateService(ABC):
    """Interface for notification template operations."""
    
    @abstractmethod
    async def render_template(
        self,
        template: NotificationTemplate,
        variables: Dict[str, Any],
        channel: DeliveryChannel
    ) -> Dict[str, str]:
        """Render notification template for specific channel."""
        pass
    
    @abstractmethod
    async def create_custom_template(
        self,
        name: str,
        content: Dict[DeliveryChannel, str],
        variables: List[str]
    ) -> str:
        """Create a custom notification template."""
        pass
    
    @abstractmethod
    async def get_template_variables(self, template: NotificationTemplate) -> List[str]:
        """Get required variables for a template."""
        pass


class INotificationPreferences(ABC):
    """Interface for user notification preferences."""
    
    @abstractmethod
    async def get_user_preferences(self, user_id: UUID) -> Dict[str, Any]:
        """Get notification preferences for a user."""
        pass
    
    @abstractmethod
    async def update_user_preferences(
        self,
        user_id: UUID,
        preferences: Dict[str, Any]
    ) -> None:
        """Update notification preferences for a user."""
        pass
    
    @abstractmethod
    async def is_channel_enabled(self, user_id: UUID, channel: DeliveryChannel) -> bool:
        """Check if user has enabled specific notification channel."""
        pass
    
    @abstractmethod
    async def get_preferred_channels(self, user_id: UUID) -> List[DeliveryChannel]:
        """Get user's preferred notification channels."""
        pass


class INotificationQueue(ABC):
    """Interface for notification queue management."""
    
    @abstractmethod
    async def enqueue(
        self,
        notification: Notification,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        delay_seconds: int = 0
    ) -> str:
        """Add notification to processing queue."""
        pass
    
    @abstractmethod
    async def dequeue(self, batch_size: int = 10) -> List[Notification]:
        """Get notifications from queue for processing."""
        pass
    
    @abstractmethod
    async def requeue(self, notification_id: UUID, delay_seconds: int = 300) -> bool:
        """Re-add failed notification to queue with delay."""
        pass
    
    @abstractmethod
    async def get_queue_size(self, priority: Optional[NotificationPriority] = None) -> int:
        """Get current queue size."""
        pass


class INotificationAnalytics(ABC):
    """Interface for notification analytics and metrics."""
    
    @abstractmethod
    async def track_notification_sent(
        self,
        notification_id: UUID,
        channel: DeliveryChannel,
        success: bool
    ) -> None:
        """Track notification delivery attempt."""
        pass
    
    @abstractmethod
    async def track_notification_opened(self, notification_id: UUID) -> None:
        """Track notification open/read event."""
        pass
    
    @abstractmethod
    async def get_delivery_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        channel: Optional[DeliveryChannel] = None
    ) -> Dict[str, Any]:
        """Get delivery metrics for time period."""
        pass
    
    @abstractmethod
    async def get_user_engagement_metrics(self, user_id: UUID) -> Dict[str, Any]:
        """Get engagement metrics for specific user."""
        pass


class INotificationScheduler(ABC):
    """Interface for notification scheduling operations."""
    
    @abstractmethod
    async def schedule_notification(
        self,
        user_id: UUID,
        message: str,
        notification_type: NotificationType,
        scheduled_at: datetime,
        timezone: Optional[str] = None
    ) -> UUID:
        """Schedule a notification for future delivery."""
        pass
    
    @abstractmethod
    async def schedule_recurring_notification(
        self,
        user_id: UUID,
        message: str,
        notification_type: NotificationType,
        cron_expression: str,
        timezone: Optional[str] = None
    ) -> UUID:
        """Schedule a recurring notification."""
        pass
    
    @abstractmethod
    async def cancel_scheduled_notification(self, schedule_id: UUID) -> bool:
        """Cancel a scheduled notification."""
        pass
    
    @abstractmethod
    async def get_scheduled_notifications(self, user_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Get scheduled notifications."""
        pass


class INotificationEventHandler(ABC):
    """Interface for handling notification-related events."""
    
    @abstractmethod
    async def handle_media_processing_complete(self, event: Dict[str, Any]) -> None:
        """Handle media processing completion event."""
        pass
    
    @abstractmethod
    async def handle_user_registration(self, event: Dict[str, Any]) -> None:
        """Handle user registration event."""
        pass
    
    @abstractmethod
    async def handle_system_alert(self, event: Dict[str, Any]) -> None:
        """Handle system alert event."""
        pass
    
    @abstractmethod
    async def handle_subscription_event(self, event: Dict[str, Any]) -> None:
        """Handle subscription-related event."""
        pass


class INotificationDeliveryService(ABC):
    """Interface for coordinating notification delivery across channels."""
    
    @abstractmethod
    async def deliver_notification(
        self,
        notification: Notification,
        preferred_channels: List[DeliveryChannel],
        fallback_channels: Optional[List[DeliveryChannel]] = None
    ) -> Dict[DeliveryChannel, bool]:
        """Deliver notification through preferred channels with fallback."""
        pass
    
    @abstractmethod
    async def get_optimal_delivery_time(self, user_id: UUID, timezone: Optional[str] = None) -> datetime:
        """Get optimal delivery time for user based on preferences and timezone."""
        pass
    
    @abstractmethod
    async def batch_deliver(self, notifications: List[Notification]) -> Dict[UUID, Dict[str, Any]]:
        """Deliver multiple notifications efficiently."""
        pass