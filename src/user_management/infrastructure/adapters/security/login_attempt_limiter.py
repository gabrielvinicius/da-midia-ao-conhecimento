"""Adaptadores de LoginAttemptLimiterPort: Redis (produção) e memória."""
from __future__ import annotations

import time
from typing import Callable, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class InMemoryLoginAttemptLimiter:
    """Contagem em memória do processo. Usada em testes e como reserva do Redis."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._failures: Dict[str, tuple[int, float]] = {}  # chave -> (falhas, fim da janela)
        self._blocked_until: Dict[str, float] = {}

    async def retry_after(self, key: str) -> int:
        until = self._blocked_until.get(key)
        if until is None:
            return 0
        remaining = until - self._clock()
        if remaining <= 0:
            self._blocked_until.pop(key, None)
            return 0
        return int(remaining) + 1

    async def register_failure(self, key: str, limit: int, window_seconds: int) -> None:
        now = self._clock()
        count, window_end = self._failures.get(key, (0, now + window_seconds))
        if now > window_end:
            count, window_end = 0, now + window_seconds
        count += 1
        self._failures[key] = (count, window_end)
        if count >= limit:
            self._blocked_until[key] = now + window_seconds
            self._failures.pop(key, None)

    async def reset(self, key: str) -> None:
        self._failures.pop(key, None)
        self._blocked_until.pop(key, None)


class RedisLoginAttemptLimiter:
    """Contagem compartilhada entre processos da API via Redis.

    Se o Redis ficar indisponível, usa a contagem em memória em vez de
    bloquear todos os logins.
    """

    PREFIX = "login_limiter"

    def __init__(self, redis_client, fallback: Optional[InMemoryLoginAttemptLimiter] = None) -> None:
        self._redis = redis_client
        self._fallback = fallback or InMemoryLoginAttemptLimiter()

    def _keys(self, key: str) -> tuple[str, str]:
        return f"{self.PREFIX}:fail:{key}", f"{self.PREFIX}:block:{key}"

    async def retry_after(self, key: str) -> int:
        _, block_key = self._keys(key)
        try:
            ttl = await self._redis.ttl(block_key)
            return max(int(ttl), 0)
        except Exception as exc:
            logger.warning("login_limiter.redis_unavailable", error=str(exc))
            return await self._fallback.retry_after(key)

    async def register_failure(self, key: str, limit: int, window_seconds: int) -> None:
        fail_key, block_key = self._keys(key)
        try:
            count = await self._redis.incr(fail_key)
            if count == 1:
                await self._redis.expire(fail_key, window_seconds)
            if count >= limit:
                await self._redis.set(block_key, 1, ex=window_seconds)
                await self._redis.delete(fail_key)
        except Exception as exc:
            logger.warning("login_limiter.redis_unavailable", error=str(exc))
            await self._fallback.register_failure(key, limit, window_seconds)

    async def reset(self, key: str) -> None:
        try:
            await self._redis.delete(*self._keys(key))
        except Exception as exc:
            logger.warning("login_limiter.redis_unavailable", error=str(exc))
        await self._fallback.reset(key)


def build_login_attempt_limiter(redis_url: Optional[str]):
    """Redis quando configurado; senão, contagem em memória."""
    if redis_url:
        try:
            from redis import asyncio as redis_asyncio

            return RedisLoginAttemptLimiter(redis_asyncio.from_url(redis_url))
        except Exception as exc:  # pacote ausente ou URL inválida
            logger.warning("login_limiter.redis_init_failed", error=str(exc))
    return InMemoryLoginAttemptLimiter()
