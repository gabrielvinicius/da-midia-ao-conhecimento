from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from src.notifications.infrastructure.adapters.websockets.connection_manager import (
    manager,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("notifications.realtime")


class RedisNotificationPubSubBridge:
    """Bridge Redis Pub/Sub -> WebSocket manager (processo da API)."""

    def __init__(self, *, redis_url: str | None = None, channel: str = "notifications"):
        self._redis_url = redis_url or settings.redis_url
        self._channel = channel
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="notifications-redis-bridge")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        client = aioredis.from_url(self._redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(self._channel)
        logger.info("notifications.realtime.bridge_started", channel=self._channel)

        try:
            while not self._stop_event.is_set():
                message: Any = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(0.05)
                    continue

                try:
                    payload = json.loads(message.get("data") or "{}")
                except Exception:
                    continue

                user_id = payload.get("user_id")
                event_payload = payload.get("payload") or {}
                notification_id = event_payload.get("notification_id")

                if not user_id:
                    continue
                try:
                    ok = await manager.send_to_user(user_id, event_payload)
                    if ok and notification_id:
                        async with AsyncSessionLocal() as session:
                            repo = NotificationRepository(db=session)
                            await repo.mark_as_delivered(str(notification_id))
                except Exception as exc:  # pragma: no cover
                    logger.warning(
                        "notifications.realtime.send_failed",
                        user_id=str(user_id),
                        error=str(exc),
                    )
        finally:
            try:
                await pubsub.unsubscribe(self._channel)
                await pubsub.close()
            finally:
                await client.aclose()
            logger.info("notifications.realtime.bridge_stopped", channel=self._channel)


__all__ = ["RedisNotificationPubSubBridge"]
