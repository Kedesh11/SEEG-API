"""
Configuration d'environnement Alembic.
Respecte le principe de responsabilité unique (Single Responsibility Principle).
"""

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
# from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config.config import settings
from app.models.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Retourne l'URL de la base de données."""
    # Utiliser l'URL depuis alembic.ini si disponible, sinon depuis settings
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    
    base_url = settings.DATABASE_URL_SYNC
    # Forcer SSL requis pour Azure si non présent (sauf localhost)
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return base_url  # Pas de SSL pour connexions locales
    return base_url + ("&sslmode=require" if "?" in base_url else "?sslmode=require")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


# Mode ONLINE en moteur synchrone

def run_migrations_online() -> None:
    """Run migrations in 'online' mode (sync engine)."""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
