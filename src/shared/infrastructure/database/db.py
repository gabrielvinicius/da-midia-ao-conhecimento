"""Lightweight SQLAlchemy helpers for tests and local usage."""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
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

SessionLocal = sessionmaker(bind=engine_sync)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

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


def get_sync_db() -> Generator[Session, None, None]:
    """Provide a synchronous SQLAlchemy session (sem commit automático).

    Mesma estratégia do `get_db()`: commit explícito nos repositórios/adapters.
    """
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Compatibility alias kept for callers; prefer get_db()."""
    return get_db()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a managed session (sem commit automático)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Synchronous context manager for SQLAlchemy session (sem commit automático)."""
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
