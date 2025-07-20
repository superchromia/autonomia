from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import os

# add your model's MetaData object here
# for 'autogenerate' support
from models.base import Base
from models.chat_config import ChatConfig
from models.event import Event

target_metadata = Base.metadata


# Get database URL from environment variables
def get_database_url():
    return os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram"
    )


def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    from urllib.parse import urlparse

    import psycopg2

    try:
        url = get_database_url()
        parsed_url = urlparse(url)

        # Connect to postgres database
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            user=parsed_url.username,
            password=parsed_url.password,
            database="postgres",
        )

        # Set autocommit to avoid transaction block issues
        conn.autocommit = True

        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (parsed_url.path[1:],)
        )

        if not cursor.fetchone():
            print(f"Creating database: {parsed_url.path[1:]}")
            # Create database
            cursor.execute(f'CREATE DATABASE "{parsed_url.path[1:]}"')
            print("Database created successfully")
        else:
            print("Database already exists")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Could not create database automatically: {e}")
        print("Continuing with existing database connection...")


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
    # Create database if it doesn't exist
    try:
        create_database_if_not_exists()
    except Exception as e:
        print(f"Database creation failed: {e}")

    url = get_database_url()
    # For async database use sync URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create database if it doesn't exist
    try:
        create_database_if_not_exists()
    except Exception as e:
        print(f"Database creation failed: {e}")

    # Get URL from environment variables
    url = get_database_url()
    # For async database use sync URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    # Create configuration with URL from environment variables
    config.set_main_option("sqlalchemy.url", url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
