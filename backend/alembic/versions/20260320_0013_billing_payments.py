"""add billing payment ledger

Revision ID: 20260320_0013
Revises: 20260320_0012
Create Date: 2026-03-26 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0013"
down_revision = "20260320_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_invoices", sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("billing_invoices", sa.Column("due_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("billing_invoices", sa.Column("payment_status", sa.String(length=30), nullable=False, server_default="unpaid"))

    op.execute("UPDATE billing_invoices SET paid_amount = 0, due_amount = total_amount, payment_status = 'unpaid' WHERE status = 'posted'")
    op.execute("UPDATE billing_invoices SET paid_amount = 0, due_amount = 0, payment_status = 'unpaid' WHERE status = 'void'")

    op.create_table(
        "billing_payments",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receipt_number", sa.String(length=50), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name=op.f("fk_billing_payments_branch_id_branches")),
        sa.ForeignKeyConstraint(["collected_by_user_id"], ["users.id"], name=op.f("fk_billing_payments_collected_by_user_id_users")),
        sa.ForeignKeyConstraint(["invoice_id"], ["billing_invoices.id"], name=op.f("fk_billing_payments_invoice_id_billing_invoices")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_billing_payments_patient_id_patients")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_payments")),
        sa.UniqueConstraint("receipt_number", name=op.f("uq_billing_payments_receipt_number")),
    )
    op.create_index(op.f("ix_billing_payments_receipt_number"), "billing_payments", ["receipt_number"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_billing_payments_receipt_number"), table_name="billing_payments")
    op.drop_table("billing_payments")
    op.drop_column("billing_invoices", "payment_status")
    op.drop_column("billing_invoices", "due_amount")
    op.drop_column("billing_invoices", "paid_amount")
