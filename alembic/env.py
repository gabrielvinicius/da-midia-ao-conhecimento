import asyncio
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# ---------- Importe todos os modelos aqui ----------
# Import all models to ensure they are registered with SQLAlchemy
from src.shared.infrastructure.database import Base  # Importar a Base
from src.shared.config.settings import settings

# Import all INFRASTRUCTURE MODELS to ensure they are registered with the Base metadata
# Note: Do NOT import Domain Entities here; they are not SQLAlchemy models.
import src.user_management.infrastructure.user_model
import src.media_management.infrastructure.persistence
import src.media_processing.transcription.infrastructure.transcription_model
import src.notifications.infrastructure.models
import src.text_analysis.infrastructure.repository_sqlalchemy

# ---------------------------------------------------

load_dotenv(".env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Mantém a URL original com +asyncpg
config.set_main_option("sqlalchemy.url", settings.database_url)

# Define os metadados para o Alembic detectar as mudanças
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())