from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from src.shared.domain.base_entity import BaseEntity


class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBSOCKET = "websocket"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Notification(BaseEntity):
    """Notification aggregate root."""

    user_id: UUID
    type: NotificationType
    content: str
    priority: NotificationPriority
    status: NotificationStatus
    template_name: Optional[str]
    variables: Dict[str, Any]
    error_message: Optional[str]
    sent_at: Optional[datetime.datetime]
    delivered_at: Optional[datetime.datetime]
    opened_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    retries: int
    max_retries: int

    def __init__(
        self,
        user_id: UUID,
        type: NotificationType,
        content: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        status: NotificationStatus = NotificationStatus.PENDING,
        template_name: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime.datetime] = None,
        delivered_at: Optional[datetime.datetime] = None,
        opened_at: Optional[datetime.datetime] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        id: Optional[UUID] = None,
        retries: int = 0,
        max_retries: int = 3,
    ):
        super().__init__(id or uuid4())
        self.user_id = user_id
        self.type = type
        self.content = content
        self.priority = priority
        self.status = status
        self.template_name = template_name
        self.variables = variables or {}
        self.error_message = error_message
        self.sent_at = sent_at
        self.delivered_at = delivered_at
        self.opened_at = opened_at
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = updated_at or datetime.datetime.now(datetime.timezone.utc)
        self.retries = retries
        self.max_retries = max_retries

    def mark_as_sent(self) -> None:
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def mark_as_delivered(self) -> None:
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def mark_as_opened(self) -> None:
        self.status = NotificationStatus.READ
        self.opened_at = datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def mark_as_failed(self, error: str) -> None:
        self.status = NotificationStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.retries += 1

    def can_retry(self) -> bool:
        return (
            self.status == NotificationStatus.FAILED
            and self.retries < self.max_retries
        )

    def is_expired(self, expiry_hours: int = 24) -> bool:
        if not self.created_at:
            return False
        delta = datetime.datetime.now(datetime.timezone.utc) - self.created_at
        return delta.total_seconds() >= expiry_hours * 3600
