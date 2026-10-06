"""Aviso ao usuário sobre o processamento das suas mídias.

Entregue pelo WebSocket; o ciclo é: criado → enviado → entregue → lido.
Antes, a entidade previa e-mail, SMS, push, modelos e novas tentativas que
nada usava.
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from src.shared.domain.base_entity import BaseEntity
from src.shared.domain.time.clock import utcnow


class NotificationType(str, Enum):
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


class Notification(BaseEntity):
    """Notification aggregate root."""

    def __init__(
        self,
        user_id: UUID,
        content: str,
        type: NotificationType = NotificationType.WEBSOCKET,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        status: NotificationStatus = NotificationStatus.PENDING,
        variables: Optional[Dict[str, Any]] = None,
        sent_at: Optional[datetime.datetime] = None,
        delivered_at: Optional[datetime.datetime] = None,
        opened_at: Optional[datetime.datetime] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        id: Optional[UUID] = None,
    ):
        super().__init__(id or uuid4())
        self.user_id = user_id
        self.type = type
        self.content = content
        self.priority = priority
        self.status = status
        self.variables = variables or {}
        self.sent_at = sent_at
        self.delivered_at = delivered_at
        self.opened_at = opened_at
        self.created_at = created_at or utcnow()
        self.updated_at = updated_at or self.created_at

    def mark_as_sent(self) -> None:
        self.sent_at = self.updated_at = utcnow()
        self.status = NotificationStatus.SENT

    def mark_as_opened(self) -> None:
        """Lido pelo usuário (a entrega pelo WebSocket é gravada pelo repositório)."""
        self.opened_at = self.updated_at = utcnow()
        self.status = NotificationStatus.READ
