import os
from logging.config import fileConfig
from urllib.parse import quote_plus  # Import para tratamento de senhas especiais

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Carrega variáveis do .env
load_dotenv(dotenv_path='.env')  # Ajuste o caminho se necessário

config = context.config

# Configuração do sistema de logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Lógica para obter a URI do banco de dados
def get_database_uri():
    # Tenta usar DB_URI direto
    db_uri = os.getenv("DB_URI")
    if db_uri:
        return db_uri

    # Monta a URI a partir de variáveis individuais
    required_vars = ['DB_SCHEME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise RuntimeError(f"Variáveis de ambiente faltando: {', '.join(missing_vars)}")

    # Trata caracteres especiais na senha
    password = quote_plus(os.getenv("DB_PASSWORD"))

    return (
        f"{os.getenv('DB_SCHEME').replace('+asyncpg', '')}://"
        f"{os.getenv('DB_USER')}:{password}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/"
        f"{os.getenv('DB_NAME')}"
    )


# Configura a URI do banco no Alembic
try:
    database_uri = get_database_uri()
    config.set_main_option("sqlalchemy.url", database_uri)
except RuntimeError as e:
    raise SystemExit(f"Erro na configuração do banco: {e}")

# Importa os modelos para suporte ao autogenerate
from src.shared.infrastructure.database import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrations no modo offline."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrations no modo online."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
