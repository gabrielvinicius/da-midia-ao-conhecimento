"""Domain entities for the notifications module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from src.shared.domain.base_entity import Entity, AggregateRoot
from src.shared.utils.time_utils import utcnow


class NotificationType(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"
    PUSH = "PUSH"
    WEBSOCKET = "WEBSOCKET"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


@dataclass(kw_only=True)
class Notification(AggregateRoot):
    """Notification entity following domain-driven design principles."""
    
    user_id: UUID
    type: NotificationType
    content: str
    subject: Optional[str] = None
    status: NotificationStatus = NotificationStatus.PENDING
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Metadata and tracking (created_at inherited from AggregateRoot -> Entity)
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    
    # Retry and error handling
    retries: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    
    # Additional data
    extra_data: Dict[str, Any] = field(default_factory=dict)
    template_name: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)

    def mark_as_sent(self) -> None:
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = utcnow()

    def mark_as_delivered(self) -> None:
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = utcnow()

    def mark_as_failed(self, error_message: str) -> None:
        """Mark notification as failed with error message."""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.retries += 1

    def mark_as_opened(self) -> None:
        """Mark notification as opened/read."""
        self.opened_at = utcnow()

    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retries < self.max_retries and self.status == NotificationStatus.FAILED

    def is_expired(self, expiry_hours: int = 24) -> bool:
        """Check if notification has expired."""
        if not self.created_at:
            return False

        expiry_time = self.created_at + timedelta(hours=expiry_hours)
        return utcnow() > expiry_time


@dataclass(kw_only=True)
class NotificationPreference(Entity):
    """User notification preferences entity."""
    
    user_id: UUID
    
    # Channel preferences
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    websocket_enabled: bool = True
    
    # Contact information
    phone_number: Optional[str] = None
    push_token: Optional[str] = None
    
    # Timing preferences
    timezone: str = "UTC"
    quiet_hours_start: Optional[datetime] = None # Note: Time in DB, datetime in domain for simpler handling or specific Time type wrapper
    quiet_hours_end: Optional[datetime] = None
    
    # Content preferences
    preferences: Dict[str, bool] = field(default_factory=lambda: {
        "marketing": True,
        "system_alerts": True,
        "processing_updates": True,
        "security_alerts": True
    })
    
    # created_at, updated_at inherited

    def is_channel_enabled(self, channel: str) -> bool:
        """Check if specific channel is enabled."""
        channel_map = {
            "email": self.email_enabled,
            "sms": self.sms_enabled,
            "push": self.push_enabled,
            "websocket": self.websocket_enabled
        }
        return channel_map.get(channel, False)


@dataclass(kw_only=True)
class NotificationTemplate(Entity):
    """Notification template entity."""
    
    name: str
    description: Optional[str] = None
    
    # Template content
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    email_html_body: Optional[str] = None
    sms_content: Optional[str] = None
    push_title: Optional[str] = None
    push_body: Optional[str] = None
    websocket_content: Optional[str] = None
    
    # Metadata
    variables: list[str] = field(default_factory=list)
    category: Optional[str] = None
    is_active: bool = True
    
    # created_at, updated_at inherited

    def get_content_for_channel(self, channel: str) -> Optional[str]:
        """Get template content for specific channel."""
        channel_map = {
            "email": self.email_body,
            "sms": self.sms_content,
            "push": self.push_body,
            "websocket": self.websocket_content
        }
        return channel_map.get(channel)