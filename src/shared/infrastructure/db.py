"""Lightweight SQLAlchemy helpers for tests and local usage."""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Union

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.shared.infrastructure.settings import settings
from src.shared.infrastructure.logging import get_logger


engine_sync = create_engine(settings.sync_database_url, future=True, isolation_level="READ COMMITTED")
engine = create_async_engine(settings.database_url, future=True, isolation_level="READ COMMITTED")

SessionLocal = sessionmaker(bind=engine_sync)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

logger = get_logger("database")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_db() -> Generator[Session, None, None]:
    """Provide a synchronous SQLAlchemy session."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


from contextlib import contextmanager

@contextmanager
def get_sync_session():
    """Synchronous context manager for SQLAlchemy session."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Compatibility alias used by legacy code."""
    return get_db()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a managed session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Synchronous context manager for SQLAlchemy session."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
