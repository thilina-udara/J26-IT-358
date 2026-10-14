import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure market-profit root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for Component 1
target_metadata = Base.metadata

# Dedicated Alembic version table to prevent collisions in the shared PostgreSQL DB
VERSION_TABLE_NAME = "alembic_version_market_profit"


def include_object(object, name, type_, reflected, compare_to):
    """
    Strict filter to exclude PostGIS spatial extensions, tiger tables, topology tables,
    and tables owned by other research components (Cultivation, Waste, Climate).
    Only tables registered in Component 1's Base.metadata are tracked.
    """
    if type_ == "table":
        # Only manage tables explicitly registered in this microservice's ORM metadata
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Emits SQL statements directly without opening an active DB connection.
    Credentials are not printed to logs.
    """
    url = settings.get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE_NAME,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using the shared SQLAlchemy engine.
    """
    from app.core.database import engine

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE_NAME,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
