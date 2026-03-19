"""add billing void lifecycle fields

Revision ID: 20260320_0004
Revises: 20260320_0003
Create Date: 2026-03-20 01:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0004"
down_revision = "20260320_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_invoices", sa.Column("status", sa.String(length=30), nullable=False, server_default="posted"))
    op.add_column("billing_invoices", sa.Column("void_reason", sa.Text(), nullable=True))
    op.add_column("billing_invoices", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_invoices", sa.Column("voided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_billing_invoices_voided_by_user_id_users"),
        "billing_invoices",
        "users",
        ["voided_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_billing_invoices_voided_by_user_id_users"), "billing_invoices", type_="foreignkey")
    op.drop_column("billing_invoices", "voided_by_user_id")
    op.drop_column("billing_invoices", "voided_at")
    op.drop_column("billing_invoices", "void_reason")
    op.drop_column("billing_invoices", "status")
