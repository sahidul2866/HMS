"""add billing refunds

Revision ID: 20260320_0015
Revises: 20260320_0014
Create Date: 2026-03-26 03:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0015"
down_revision = "20260320_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_invoices", sa.Column("refunded_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))

    op.create_table(
        "billing_refunds",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("refund_number", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refunded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name=op.f("fk_billing_refunds_branch_id_branches")),
        sa.ForeignKeyConstraint(["invoice_id"], ["billing_invoices.id"], name=op.f("fk_billing_refunds_invoice_id_billing_invoices")),
        sa.ForeignKeyConstraint(["payment_id"], ["billing_payments.id"], name=op.f("fk_billing_refunds_payment_id_billing_payments")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_billing_refunds_patient_id_patients")),
        sa.ForeignKeyConstraint(["refunded_by_user_id"], ["users.id"], name=op.f("fk_billing_refunds_refunded_by_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_refunds")),
        sa.UniqueConstraint("refund_number", name=op.f("uq_billing_refunds_refund_number")),
    )
    op.create_index(op.f("ix_billing_refunds_refund_number"), "billing_refunds", ["refund_number"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_billing_refunds_refund_number"), table_name="billing_refunds")
    op.drop_table("billing_refunds")
    op.drop_column("billing_invoices", "refunded_amount")
