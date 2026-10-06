"""Lightweight SQLAlchemy helpers for tests and local usage."""
from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.observability.logging.logging_config import get_logger

_async_url = settings.database_url
_sync_url = settings.sync_database_url

_is_sqlite = _sync_url.startswith("sqlite")

engine_sync = create_engine(
    _sync_url,
    future=True,
    isolation_level=None if _is_sqlite else "READ COMMITTED",
)

# Só cria engine assíncrono quando o driver for async; caso contrário, deixe None.
engine = None
if "+async" in _async_url or "aiosqlite" in _async_url:
    connect_args = {"check_same_thread": False} if _is_sqlite else {}
    engine = create_async_engine(
        _async_url,
        future=True,
        isolation_level=None if _is_sqlite else "READ COMMITTED",
        poolclass=NullPool,  # evita reuse de conexão entre tasks (worker)
        connect_args=connect_args,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# --- Uma sessão por requisição --------------------------------------------
# Os módulos da API são montados uma vez, na inicialização. Antes, recebiam a
# sessão aberta nesse momento, e ela era compartilhada por todas as
# requisições: duas requisições simultâneas falhavam ("concurrent operations
# are not permitted") e o estado de transação de uma podia vazar para outra.
# Agora recebem RequestScopedSession, que entrega a cada requisição a sua
# própria sessão (escopo definido por DbSessionScopeMiddleware).
_request_scope: ContextVar[str] = ContextVar("db_request_scope", default="global")
RequestScopedSession = async_scoped_session(AsyncSessionLocal, scopefunc=_request_scope.get)


class DbSessionScopeMiddleware:
    """Abre um escopo de sessão por requisição HTTP/WebSocket e o fecha no fim."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        token = _request_scope.set(uuid4().hex)
        try:
            await self.app(scope, receive, send)
        finally:
            try:
                await RequestScopedSession.remove()
            finally:
                _request_scope.reset(token)


Base = declarative_base()

logger = get_logger("database")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session (sem commit automático).

    Estratégia única de transação/commit:
    - A sessão é criada por request/task e **não** comita automaticamente no final.
    - A responsabilidade de `commit()` fica nos repositórios/adapters (ou UoW),
      mantendo o fluxo explícito e evitando commits duplicados.
    - Em caso de exceção, fazemos rollback defensivo.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
