"""Tamanho das filas do Celery no Redis (o broker guarda cada fila numa lista)."""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import redis.asyncio as aioredis
import structlog

from src.shared.events.integration_events import HEAVY_WORKER_QUEUES, LIGHT_WORKER_QUEUES

logger = structlog.get_logger(__name__)


class RedisQueueDepthAdapter:
    def __init__(self, redis_url: str, queues: Sequence[str] = (*HEAVY_WORKER_QUEUES, *LIGHT_WORKER_QUEUES)) -> None:
        self._redis_url = redis_url
        self._queues = tuple(queues)

    async def waiting_tasks(self) -> Optional[Dict[str, int]]:
        client = aioredis.from_url(self._redis_url, socket_connect_timeout=2, socket_timeout=2)
        try:
            return {queue: int(await client.llen(queue)) for queue in self._queues}
        except Exception as exc:  # a tela mostra a fila mesmo sem o broker
            logger.warning("admin.queue_depth.unavailable", error=str(exc))
            return None
        finally:
            await client.aclose()


__all__ = ["RedisQueueDepthAdapter"]
