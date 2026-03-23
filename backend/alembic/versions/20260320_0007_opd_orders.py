"""add opd visit orders

Revision ID: 20260320_0007
Revises: 20260320_0006
Create Date: 2026-03-20 17:50:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0007"
down_revision = "20260320_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opd_visit_orders",
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_type", sa.String(length=30), nullable=False),
        sa.Column("item_name", sa.String(length=180), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["opd_visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("opd_visit_orders")
