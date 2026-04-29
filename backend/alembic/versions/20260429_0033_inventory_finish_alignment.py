"""Align inventory demo/reporting columns.

Revision ID: 20260429_0033
Revises: 20260429_0032
Create Date: 2026-04-29 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "20260429_0033"
down_revision = "20260429_0032"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    if not _has_column("reagent_test_mappings", "analyzer_name"):
        op.add_column("reagent_test_mappings", sa.Column("analyzer_name", sa.String(150), nullable=True))
    if not _has_column("reagent_test_mappings", "volume_used_per_test"):
        op.add_column("reagent_test_mappings", sa.Column("volume_used_per_test", sa.Numeric(14, 3), nullable=True))
    if not _has_column("reagent_test_mappings", "remark"):
        op.add_column("reagent_test_mappings", sa.Column("remark", sa.Text(), nullable=True))


def downgrade():
    if _has_column("reagent_test_mappings", "remark"):
        op.drop_column("reagent_test_mappings", "remark")
    if _has_column("reagent_test_mappings", "volume_used_per_test"):
        op.drop_column("reagent_test_mappings", "volume_used_per_test")
    if _has_column("reagent_test_mappings", "analyzer_name"):
        op.drop_column("reagent_test_mappings", "analyzer_name")
