"""SQLAlchemy models for the notifications module."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    Uuid
)

from src.notifications.domain.notification import (
    Notification as DomainNotification,
    NotificationPreference as DomainPreference,
    NotificationTemplate as DomainTemplate,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from src.shared.infrastructure.db import Base
from src.shared.utils.time_utils import utcnow


class NotificationModel(Base):
    """Persistence model for Notifications."""

    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False)
    content = Column(Text, nullable=False)
    subject = Column(String(255), nullable=True)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)

    created_at = Column(DateTime, default=utcnow)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)

    retries = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)

    extra_data = Column(JSON, nullable=True)
    template_name = Column(String(100), nullable=True)
    variables = Column(JSON, nullable=True)

    def to_domain(self) -> DomainNotification:
        return DomainNotification(
            id=self.id,
            user_id=self.user_id,
            type=self.type,
            content=self.content,
            subject=self.subject,
            status=self.status,
            priority=self.priority,
            created_at=self.created_at,
            scheduled_at=self.scheduled_at,
            sent_at=self.sent_at,
            delivered_at=self.delivered_at,
            opened_at=self.opened_at,
            retries=self.retries,
            max_retries=self.max_retries,
            error_message=self.error_message,
            extra_data=self.extra_data or {},
            template_name=self.template_name,
            variables=self.variables or {}
        )

    @classmethod
    def from_domain(cls, notification: DomainNotification) -> "NotificationModel":
        return cls(
            id=notification.id,
            user_id=notification.user_id,
            type=notification.type,
            content=notification.content,
            subject=notification.subject,
            status=notification.status,
            priority=notification.priority,
            created_at=notification.created_at,
            scheduled_at=notification.scheduled_at,
            sent_at=notification.sent_at,
            delivered_at=notification.delivered_at,
            opened_at=notification.opened_at,
            retries=notification.retries,
            max_retries=notification.max_retries,
            error_message=notification.error_message,
            extra_data=notification.extra_data,
            template_name=notification.template_name,
            variables=notification.variables
        )


class NotificationPreferenceModel(Base):
    """Persistence model for Notification Preferences."""

    __tablename__ = "notification_preferences"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    push_enabled = Column(Boolean, default=True)
    websocket_enabled = Column(Boolean, default=True)

    phone_number = Column(String(20), nullable=True)
    push_token = Column(String(255), nullable=True)

    timezone = Column(String(50), default="UTC")
    quiet_hours_start = Column(Time, nullable=True)
    quiet_hours_end = Column(Time, nullable=True)

    preferences = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_domain(self) -> DomainPreference:
        return DomainPreference(
            id=self.id,
            user_id=self.user_id,
            email_enabled=self.email_enabled,
            sms_enabled=self.sms_enabled,
            push_enabled=self.push_enabled,
            websocket_enabled=self.websocket_enabled,
            phone_number=self.phone_number,
            push_token=self.push_token,
            timezone=self.timezone,
            quiet_hours_start=self.quiet_hours_start,
            quiet_hours_end=self.quiet_hours_end,
            preferences=self.preferences or {},
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @classmethod
    def from_domain(cls, preference: DomainPreference) -> "NotificationPreferenceModel":
        return cls(
            id=preference.id,
            user_id=preference.user_id,
            email_enabled=preference.email_enabled,
            sms_enabled=preference.sms_enabled,
            push_enabled=preference.push_enabled,
            websocket_enabled=preference.websocket_enabled,
            phone_number=preference.phone_number,
            push_token=preference.push_token,
            timezone=preference.timezone,
            quiet_hours_start=preference.quiet_hours_start,
            quiet_hours_end=preference.quiet_hours_end,
            preferences=preference.preferences,
            created_at=preference.created_at,
            updated_at=preference.updated_at
        )


class NotificationTemplateModel(Base):
    """Persistence model for Notification Templates."""

    __tablename__ = "notification_templates"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    email_subject = Column(String(255), nullable=True)
    email_body = Column(Text, nullable=True)
    email_html_body = Column(Text, nullable=True)
    sms_content = Column(Text, nullable=True)
    push_title = Column(String(100), nullable=True)
    push_body = Column(Text, nullable=True)
    websocket_content = Column(Text, nullable=True)

    variables = Column(JSON, nullable=True)
    category = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_domain(self) -> DomainTemplate:
        return DomainTemplate(
            id=self.id,
            name=self.name,
            description=self.description,
            email_subject=self.email_subject,
            email_body=self.email_body,
            email_html_body=self.email_html_body,
            sms_content=self.sms_content,
            push_title=self.push_title,
            push_body=self.push_body,
            websocket_content=self.websocket_content,
            variables=self.variables or [],
            category=self.category,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @classmethod
    def from_domain(cls, template: DomainTemplate) -> "NotificationTemplateModel":
        return cls(
            id=template.id,
            name=template.name,
            description=template.description,
            email_subject=template.email_subject,
            email_body=template.email_body,
            email_html_body=template.email_html_body,
            sms_content=template.sms_content,
            push_title=template.push_title,
            push_body=template.push_body,
            websocket_content=template.websocket_content,
            variables=template.variables,
            category=template.category,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at
        )