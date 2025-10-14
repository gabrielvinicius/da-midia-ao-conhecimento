from sqlalchemy import create_engine, NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager

# OpenTelemetry Imports
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from src.shared.config.database_settings import DatabaseSettings
from src.shared.infrastructure.logging_config import get_logger

settings = DatabaseSettings()

# Sync Engine
engine_sync = create_engine(
    url=settings.database_url.replace('+asyncpg', ''),
    echo=True,
    pool_pre_ping=True,
    pool_timeout=30
)

# Async Engine
engine = create_async_engine(
    settings.database_url,
    echo=True,
    poolclass=NullPool,
)

# Instrument only the sync engine with OpenTelemetry (async engine doesn't support instrumentation)
SQLAlchemyInstrumentor().instrument(engine=engine_sync)


# Session factories
SessionLocal = sessionmaker(bind=engine_sync)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base model
Base = declarative_base()


# Logger para operações de banco
logger = get_logger("database")

# Async DB session dependency (e.g. for FastAPI)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    logger.debug("Abrindo sessão do banco de dados", operation="session_open")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Sessão do banco finalizada com sucesso", operation="session_commit")
        except Exception as e:
            await session.rollback()
            logger.error("Erro na sessão do banco, fazendo rollback", 
                        operation="session_rollback", error=str(e))
            raise
        finally:
            logger.debug("Fechando sessão do banco de dados", operation="session_close")


# Sync DB session dependency (e.g. for CLI tools, tests)
def get_sync_db() -> Generator[Session, None, None]:
    logger.debug("Abrindo sessão síncrona do banco de dados", operation="sync_session_open")
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
            logger.debug("Sessão síncrona finalizada com sucesso", operation="sync_session_commit")
        except Exception as e:
            session.rollback()
            logger.error("Erro na sessão síncrona, fazendo rollback", 
                        operation="sync_session_rollback", error=str(e))
            raise
        finally:
            logger.debug("Fechando sessão síncrona do banco de dados", operation="sync_session_close")


# Context manager para gerenciamento manual de sessões
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para gerenciamento manual de sessões de banco."""
    logger.debug("Criando sessão manual do banco", operation="manual_session_create")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Sessão manual commitada com sucesso", operation="manual_session_commit")
        except Exception as e:
            await session.rollback()
            logger.error("Erro na sessão manual, fazendo rollback", 
                        operation="manual_session_rollback", error=str(e))
            raise
        finally:
            await session.close()
            logger.debug("Sessão manual fechada", operation="manual_session_close")
