"""Verificação de saúde da API: banco e Redis (fila e avisos).

Responde 503 quando algo falha. Antes havia duas rotas /health: uma sempre
"healthy", sem verificar nada, e outra que respondia 200 mesmo com
"unhealthy" no corpo, de modo que o healthcheck do Docker (curl -f) nunca
via a API doente.
"""
from __future__ import annotations

from typing import Awaitable, Callable

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.database.db import AsyncSessionLocal

router = APIRouter(tags=["Health"])

TIMEOUT_SECONDS = 3


async def database_ok() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def redis_ok() -> bool:
    client = aioredis.from_url(settings.redis_url, socket_connect_timeout=TIMEOUT_SECONDS)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


CHECKS: dict[str, Callable[[], Awaitable[bool]]] = {"database": database_ok, "redis": redis_ok}


@router.get("/health", summary="Saúde da API, do banco e do Redis (503 se algum falhar)")
async def health_check() -> JSONResponse:
    results = {name: await check() for name, check in CHECKS.items()}
    healthy = all(results.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "unhealthy",
            **{name: "connected" if ok else "disconnected" for name, ok in results.items()},
        },
    )
