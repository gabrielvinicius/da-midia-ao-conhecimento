import uuid
from datetime import datetime, timedelta, time
from enum import Enum as PyEnum
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Enum, Integer, Text, ForeignKey, JSON, Boolean, Time
from sqlalchemy.dialects.postgresql import UUID
# FIXED: Domain should not import Infrastructure - Critical DDD violation
from src.shared.domain.base_entity import BaseEntity
from src.shared.infrastructure.database import Base


class NotificationType(PyEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"
    PUSH = "PUSH"
    WEBSOCKET = "WEBSOCKET"


class NotificationStatus(PyEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationPriority(PyEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Notification(Base):
    """
    Notification entity following domain-driven design principles.
    
    Represents a notification that can be sent through various channels.
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    content = Column(Text, nullable=False)
    subject = Column(String(255), nullable=True)  # For email notifications
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    
    # Metadata and tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)  # For scheduled notifications
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)  # For tracking opens/reads
    
    # Retry and error handling
    retries = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)  # For storing additional context
    template_name = Column(String(100), nullable=True)  # Template used
    variables = Column(JSON, nullable=True)  # Template variables
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.extra_data:
            self.extra_data = {}
        if not self.variables:
            self.variables = {}
    
    def mark_as_sent(self) -> None:
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
    
    def mark_as_delivered(self) -> None:
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """Mark notification as failed with error message."""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.retries += 1
    
    def mark_as_opened(self) -> None:
        """Mark notification as opened/read."""
        self.opened_at = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retries < self.max_retries and self.status == NotificationStatus.FAILED
    
    def is_expired(self, expiry_hours: int = 24) -> bool:
        """Check if notification has expired."""
        if not self.created_at:
            return False
        
        expiry_time = self.created_at + datetime.timedelta(hours=expiry_hours)
        return datetime.utcnow() > expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "type": self.type.value,
            "content": self.content,
            "subject": self.subject,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "extra_data": self.extra_data,
            "template_name": self.template_name,
            "variables": self.variables
        }


class NotificationPreference(Base):
    """
    User notification preferences entity.
    """
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Channel preferences
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    push_enabled = Column(Boolean, default=True)
    websocket_enabled = Column(Boolean, default=True)
    
    # Contact information
    phone_number = Column(String(20), nullable=True)
    push_token = Column(String(255), nullable=True)
    
    # Timing preferences
    timezone = Column(String(50), default="UTC")
    quiet_hours_start = Column(Time, nullable=True)  # e.g., 22:00
    quiet_hours_end = Column(Time, nullable=True)    # e.g., 08:00
    
    # Content preferences
    preferences = Column(JSON, nullable=True)  # Flexible preferences storage
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.preferences:
            self.preferences = {
                "marketing": True,
                "system_alerts": True,
                "processing_updates": True,
                "security_alerts": True
            }
    
    def is_channel_enabled(self, channel: str) -> bool:
        """Check if specific channel is enabled."""
        channel_map = {
            "email": self.email_enabled,
            "sms": self.sms_enabled,
            "push": self.push_enabled,
            "websocket": self.websocket_enabled
        }
        return channel_map.get(channel, False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            "user_id": str(self.user_id),
            "email_enabled": self.email_enabled,
            "sms_enabled": self.sms_enabled,
            "push_enabled": self.push_enabled,
            "websocket_enabled": self.websocket_enabled,
            "phone_number": self.phone_number,
            "push_token": self.push_token,
            "timezone": self.timezone,
            "quiet_hours_start": self.quiet_hours_start.isoformat() if self.quiet_hours_start else None,
            "quiet_hours_end": self.quiet_hours_end.isoformat() if self.quiet_hours_end else None,
            "preferences": self.preferences
        }


class NotificationTemplate(Base):
    """
    Notification template entity for reusable notification content.
    """
    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Template content for different channels
    email_subject = Column(String(255), nullable=True)
    email_body = Column(Text, nullable=True)
    email_html_body = Column(Text, nullable=True)
    sms_content = Column(Text, nullable=True)
    push_title = Column(String(100), nullable=True)
    push_body = Column(Text, nullable=True)
    websocket_content = Column(Text, nullable=True)
    
    # Template metadata
    variables = Column(JSON, nullable=True)  # Required variables
    category = Column(String(50), nullable=True)  # Template category
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.variables:
            self.variables = []
    
    def get_content_for_channel(self, channel: str) -> Optional[str]:
        """Get template content for specific channel."""
        channel_map = {
            "email": self.email_body,
            "sms": self.sms_content,
            "push": self.push_body,
            "websocket": self.websocket_content
        }
        return channel_map.get(channel)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "email_subject": self.email_subject,
            "email_body": self.email_body,
            "email_html_body": self.email_html_body,
            "sms_content": self.sms_content,
            "push_title": self.push_title,
            "push_body": self.push_body,
            "websocket_content": self.websocket_content,
            "variables": self.variables,
            "category": self.category,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
