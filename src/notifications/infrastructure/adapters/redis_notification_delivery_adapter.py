from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

from src.notifications.application.ports import NotificationDeliveryPort
from src.shared.infrastructure.config.settings import settings


class RedisNotificationDeliveryAdapter(NotificationDeliveryPort):
    """Publica notificações em um canal Redis para entrega realtime pela API.

    Importante: isto NÃO é o event bus de domínio. É um transporte de entrega
    (realtime) para o frontend via WebSocket.
    """

    def __init__(self, *, redis_url: str | None = None, channel: str = "notifications"):
        self._redis_url = redis_url or settings.redis_url
        self._channel = channel

    async def send_to_user(self, user_id: UUID, payload: Any) -> bool:
        client = aioredis.from_url(self._redis_url, decode_responses=True)
        try:
            message = json.dumps(
                {
                    "user_id": str(user_id),
                    "payload": payload,
                },
                ensure_ascii=False,
                default=str,
            )
            await client.publish(self._channel, message)
            return True
        finally:
            await client.aclose()


__all__ = ["RedisNotificationDeliveryAdapter"]

