import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure project root is on sys.path
sys.path.append(os.getcwd())

# ---------- Register all models here ----------
# Infrastructure models (SQLAlchemy)
import src.media_management.infrastructure.persistence.models  # noqa: F401
import src.media_processing.infrastructure.persistence.models  # noqa: F401
import src.notifications.infrastructure.persistence.models  # noqa: F401
import src.text_analysis.infrastructure.persistence.models  # noqa: F401
import src.text_analysis.infrastructure.persistence.knowledge_models  # noqa: F401
import src.text_analysis.infrastructure.persistence.feedback_models  # noqa: F401
import src.shared.infrastructure.persistence.processing_stats_model  # noqa: F401
import src.user_management.infrastructure.persistence.models  # noqa: F401
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.database import Base  # SQLAlchemy Base

# ---------------------------------------------------

load_dotenv(".env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Derive URL síncrona para o Alembic (evita drivers async).
_db_url = settings.database_url
if "+asyncpg" in _db_url:
    _db_url = _db_url.replace("+asyncpg", "+psycopg2")
elif "+aiosqlite" in _db_url:
    _db_url = _db_url.replace("+aiosqlite", "")

config.set_main_option("sqlalchemy.url", _db_url)

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


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
