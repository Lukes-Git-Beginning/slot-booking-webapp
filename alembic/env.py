# -*- coding: utf-8 -*-
"""
Alembic Environment Configuration

Automatische Migration-Generierung mit SQLAlchemy Models
"""

from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Import Base und alle Models
from app.models.base import Base, get_database_url
from app.models import *  # Imports alle Models (wichtig für autogenerate!)

# Alembic Config
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy MetaData für autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url mit Environment-Variable
database_url = get_database_url()
config.set_main_option('sqlalchemy.url', database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
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
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Configuration für Engine
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Type-Changes erkennen
            compare_server_default=True,  # Default-Changes erkennen
            include_schemas=False,  # Nur default schema
            # Optionale Ignores (bei Bedarf anpassen)
            # include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


# Optional: Filter welche Objects migriert werden sollen
def include_object(object, name, type_, reflected, compare_to):
    """
    Filter für autogenerate

    Return False to exclude an object from migration
    """
    # Beispiel: Ignoriere temporäre Tables
    if type_ == "table" and name.startswith("temp_"):
        return False

    # Beispiel: Ignoriere bestimmte Indexes
    if type_ == "index" and name.startswith("_"):
        return False

    return True


# Ausführen basierend auf Mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
