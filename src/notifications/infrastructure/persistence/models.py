from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)

from src.notifications.domain import (
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from src.shared.infrastructure.database.db import Base


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    type = Column(Enum(NotificationType), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(
        Enum(NotificationPriority),
        nullable=False,
        default=NotificationPriority.NORMAL,
    )
    status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )
    template_name = Column(String, nullable=True)
    variables = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    retries = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    def to_domain(self) -> Notification:
        return Notification(
            id=self.id,
            user_id=self.user_id,
            type=self.type,
            content=self.content,
            priority=self.priority,
            status=self.status,
            template_name=self.template_name,
            variables=self.variables or {},
            error_message=self.error_message,
            sent_at=self.sent_at,
            delivered_at=self.delivered_at,
            opened_at=self.opened_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
            retries=self.retries,
            max_retries=self.max_retries,
        )

    @classmethod
    def from_domain(cls, notification: Notification) -> "NotificationModel":
        return cls(
            id=notification.id,
            user_id=notification.user_id,
            type=notification.type,
            content=notification.content,
            priority=notification.priority,
            status=notification.status,
            template_name=notification.template_name,
            variables=notification.variables,
            error_message=notification.error_message,
            sent_at=notification.sent_at,
            delivered_at=notification.delivered_at,
            opened_at=notification.opened_at,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
            retries=notification.retries,
            max_retries=notification.max_retries,
        )


__all__ = ["NotificationModel"]
