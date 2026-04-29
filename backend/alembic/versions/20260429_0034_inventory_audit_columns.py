"""Add missing inventory audit columns.

Revision ID: 20260429_0034
Revises: 20260429_0033
Create Date: 2026-04-29 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260429_0034"
down_revision = "20260429_0033"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_actor_columns(table_name: str) -> None:
    if not _has_column(table_name, "created_by"):
        op.add_column(table_name, sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True))
    if not _has_column(table_name, "updated_by"):
        op.add_column(table_name, sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True))


def upgrade():
    _add_actor_columns("inventory_categories")
    _add_actor_columns("reagent_test_mappings")


def downgrade():
    for table_name in ("reagent_test_mappings", "inventory_categories"):
        if _has_column(table_name, "updated_by"):
            op.drop_column(table_name, "updated_by")
        if _has_column(table_name, "created_by"):
            op.drop_column(table_name, "created_by")
