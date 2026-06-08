"""billing return metadata

Revision ID: 20260604_0059
Revises: 20260531_0058
Create Date: 2026-06-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0059"
down_revision = "20260531_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_refunds", sa.Column("refund_type", sa.String(length=30), nullable=False, server_default="refund"))
    op.add_column("billing_refunds", sa.Column("return_items", sa.JSON(), nullable=True))
    op.alter_column("billing_refunds", "refund_type", server_default=None)


def downgrade() -> None:
    op.drop_column("billing_refunds", "return_items")
    op.drop_column("billing_refunds", "refund_type")
