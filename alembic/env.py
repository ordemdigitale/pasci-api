from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --- SQLModel/Async/Alembic integration ---
import asyncio
from sqlmodel import SQLModel
import sys
import os
import importlib
import glob
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

# Dynamically import all model modules in app/models
models_dir = os.path.join(os.path.dirname(__file__), '../app/models')
model_files = glob.glob(os.path.join(models_dir, '*.py'))
for file_path in model_files:
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    if not module_name.startswith('__'):
        importlib.import_module(f'app.models.{module_name}')

# Set target_metadata for autogenerate
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()



# --- Async migration support ---
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine

def get_url():
    # Use the same logic as your app for async DB URL
    url = settings.DATABASE_URL
    print(f"DEBUG - Original URL: {url}")
    if url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    url = url + "?ssl=disable"  # Ajoutez cette ligne
    print(f"DEBUG - Final URL: {url}")
    return url

async def run_async_migrations():
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=True,  # For SQLite, remove if not needed
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
