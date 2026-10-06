"""Adaptadores de RevokedTokensPort: Redis (produção) e memória."""
from __future__ import annotations

import time
from typing import Callable, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class InMemoryRevokedTokens:
    """Revogações do próprio processo. Usada em testes e como reserva do Redis."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._until: Dict[str, float] = {}

    async def revoke(self, token_id: str, ttl_seconds: int) -> None:
        self._until[token_id] = self._clock() + max(ttl_seconds, 1)

    async def consume(self, token_id: str, ttl_seconds: int) -> bool:
        # Leitura e escrita sem await entre elas: atômico no laço de eventos.
        if self._active(token_id):
            return False
        self._until[token_id] = self._clock() + max(ttl_seconds, 1)
        return True

    async def is_revoked(self, token_id: str) -> bool:
        return self._active(token_id)

    def _active(self, token_id: str) -> bool:
        until = self._until.get(token_id)
        if until is None:
            return False
        if until <= self._clock():
            self._until.pop(token_id, None)
            return False
        return True


class RedisRevokedTokens:
    """Revogações compartilhadas entre os processos da API, com validade igual
    à do próprio token (depois disso ele já não vale)."""

    PREFIX = "revoked_token"

    def __init__(self, redis_client, fallback: Optional[InMemoryRevokedTokens] = None) -> None:
        self._redis = redis_client
        self._fallback = fallback or InMemoryRevokedTokens()

    async def revoke(self, token_id: str, ttl_seconds: int) -> None:
        await self._fallback.revoke(token_id, ttl_seconds)
        try:
            await self._redis.set(f"{self.PREFIX}:{token_id}", 1, ex=max(ttl_seconds, 1))
        except Exception as exc:
            logger.warning("revoked_tokens.redis_unavailable", error=str(exc))

    async def consume(self, token_id: str, ttl_seconds: int) -> bool:
        """SET NX: só a primeira chamada grava; as seguintes recebem False."""
        try:
            first = await self._redis.set(f"{self.PREFIX}:{token_id}", 1, ex=max(ttl_seconds, 1), nx=True)
        except Exception as exc:
            logger.warning("revoked_tokens.redis_unavailable", error=str(exc))
            return await self._fallback.consume(token_id, ttl_seconds)
        await self._fallback.revoke(token_id, ttl_seconds)
        return bool(first)

    async def is_revoked(self, token_id: str) -> bool:
        try:
            if await self._redis.exists(f"{self.PREFIX}:{token_id}"):
                return True
        except Exception as exc:
            logger.warning("revoked_tokens.redis_unavailable", error=str(exc))
        return await self._fallback.is_revoked(token_id)


def build_revoked_tokens(redis_url: Optional[str]):
    """Redis quando configurado; senão, em memória."""
    if redis_url:
        try:
            from redis import asyncio as redis_asyncio

            return RedisRevokedTokens(redis_asyncio.from_url(redis_url))
        except Exception as exc:
            logger.warning("revoked_tokens.redis_init_failed", error=str(exc))
    return InMemoryRevokedTokens()


__all__ = ["InMemoryRevokedTokens", "RedisRevokedTokens", "build_revoked_tokens"]
