"""Formato único das mensagens enviadas ao navegador por WebSocket.

Tanto a API quanto os workers (via Redis) entregam notificações ao frontend.
As duas rotas precisam produzir a mesma mensagem, senão o cliente não a
reconhece. O envelope é ``{"kind": "new_notification", "payload": {...}}``,
e o ``payload`` tem os mesmos campos da notificação devolvida pela API REST.
"""
from __future__ import annotations

from typing import Any, Dict

from src.notifications.domain import Notification

NEW_NOTIFICATION = "new_notification"


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def realtime_message(notification: Notification) -> Dict[str, Any]:
    """Monta a mensagem de WebSocket de uma notificação já persistida."""
    return {
        "kind": NEW_NOTIFICATION,
        "payload": {
            "id": str(notification.id),
            "user_id": str(notification.user_id),
            "type": notification.type.value,
            "content": notification.content,
            "priority": notification.priority.value,
            "status": notification.status.value,
            "variables": dict(notification.variables or {}),
            "created_at": _iso(notification.created_at),
            "read": notification.opened_at is not None,
        },
    }


def notification_id_of(message: Dict[str, Any]) -> str | None:
    """Extrai o id da notificação de uma mensagem (para marcar como entregue)."""
    payload = message.get("payload") if isinstance(message, dict) else None
    if isinstance(payload, dict) and payload.get("id"):
        return str(payload["id"])
    return None


__all__ = ["NEW_NOTIFICATION", "realtime_message", "notification_id_of"]
