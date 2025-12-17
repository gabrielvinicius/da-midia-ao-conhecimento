from __future__ import annotations

from uuid import UUID

from src.notifications.application.ports import NotificationDeliveryPort
from src.notifications.infrastructure.adapters.websockets.connection_manager import (
    manager as ws_manager,
)


class WebSocketNotificationDeliveryAdapter(NotificationDeliveryPort):
    """Adapter that delivers notifications via existing WebSocket connection manager."""

    async def send_to_user(self, user_id: UUID, payload):
        return await ws_manager.send_to_user(user_id, payload)


__all__ = ["WebSocketNotificationDeliveryAdapter"]
