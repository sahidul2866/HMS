"""add billing discount settings and tracking

Revision ID: 20260413_0023
Revises: 20260411_0022
Create Date: 2026-04-13 12:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260413_0023"
down_revision = "20260411_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_invoices", sa.Column("item_discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("billing_invoices", sa.Column("invoice_discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("billing_invoice_items", sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("billing_invoice_items", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))

    op.create_table(
        "billing_settings",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("max_item_discount_percentage", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("max_invoice_discount_percentage", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id", name="uq_billing_settings_branch_id"),
    )


def downgrade() -> None:
    op.drop_table("billing_settings")
    op.drop_column("billing_invoice_items", "discount_amount")
    op.drop_column("billing_invoice_items", "discount_percentage")
    op.drop_column("billing_invoices", "invoice_discount_amount")
    op.drop_column("billing_invoices", "item_discount_amount")
