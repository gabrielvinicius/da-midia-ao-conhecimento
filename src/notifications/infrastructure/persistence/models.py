from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
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
from src.shared.infrastructure.database.types import enum_column


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    type = Column(enum_column(NotificationType), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(
        enum_column(NotificationPriority),
        nullable=False,
        default=NotificationPriority.NORMAL,
    )
    status = Column(
        enum_column(NotificationStatus),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )
    variables = Column(JSON, nullable=True)
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

    def to_domain(self) -> Notification:
        return Notification(
            id=self.id,
            user_id=self.user_id,
            type=self.type,
            content=self.content,
            priority=self.priority,
            status=self.status,
            variables=self.variables or {},
            sent_at=self.sent_at,
            delivered_at=self.delivered_at,
            opened_at=self.opened_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
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
            variables=notification.variables,
            sent_at=notification.sent_at,
            delivered_at=notification.delivered_at,
            opened_at=notification.opened_at,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
        )


__all__ = ["NotificationModel"]
