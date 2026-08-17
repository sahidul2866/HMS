"""Safely reconcile an existing model-bootstrapped database with Alembic."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.models import *  # noqa: F401,F403 - register all model tables
from app.models.base import Base

IGNORED_MODEL_TABLES = {
    # Deliberately removed by migration 20260504_0043. The legacy ORM class is
    # retained temporarily for compatibility but must not trigger migrations.
    "billing_services",
}


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    database_tables = set(inspector.get_table_names())
    model_tables = set(Base.metadata.tables) - IGNORED_MODEL_TABLES

    missing_tables = sorted(model_tables - database_tables)
    missing_columns: list[str] = []
    for table_name in sorted(model_tables & database_tables):
        database_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in Base.metadata.tables[table_name].columns:
            if column.name not in database_columns:
                missing_columns.append(f"{table_name}.{column.name}")

    alembic_config = Config("alembic.ini")
    if not missing_tables and not missing_columns:
        print("Database already matches all model tables and columns; stamping Alembic head.")
        command.stamp(alembic_config, "head")
        return

    print(
        "Database is not fully aligned; running incremental migrations "
        f"({len(missing_tables)} missing tables, {len(missing_columns)} missing columns)."
    )
    if missing_tables:
        print("Missing tables: " + ", ".join(missing_tables[:20]))
    if missing_columns:
        print("Missing columns: " + ", ".join(missing_columns[:20]))
    command.upgrade(alembic_config, "head")


if __name__ == "__main__":
    main()
