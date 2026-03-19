"""add billing module tables

Revision ID: 20260320_0002
Revises: 20260319_0001
Create Date: 2026-03-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0002"
down_revision = "20260319_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_services",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("doctor_share_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name=op.f("fk_billing_services_branch_id_branches")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_services")),
    )
    op.create_index(op.f("ix_billing_services_service_code"), "billing_services", ["service_code"], unique=False)

    op.create_table(
        "billing_invoices",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("referred_doctor_name", sa.String(length=150), nullable=True),
        sa.Column("sub_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("referred_doctor_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("billed_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name=op.f("fk_billing_invoices_branch_id_branches")),
        sa.ForeignKeyConstraint(["billed_by_user_id"], ["users.id"], name=op.f("fk_billing_invoices_billed_by_user_id_users")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_billing_invoices_patient_id_patients")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_invoices")),
        sa.UniqueConstraint("invoice_number", name=op.f("uq_billing_invoices_invoice_number")),
    )
    op.create_index(op.f("ix_billing_invoices_invoice_number"), "billing_invoices", ["invoice_number"], unique=True)

    op.create_table(
        "billing_invoice_items",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("billing_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(length=150), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("doctor_share_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("doctor_share_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["billing_service_id"], ["billing_services.id"], name=op.f("fk_billing_invoice_items_billing_service_id_billing_services")),
        sa.ForeignKeyConstraint(["invoice_id"], ["billing_invoices.id"], name=op.f("fk_billing_invoice_items_invoice_id_billing_invoices")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_invoice_items")),
    )


def downgrade() -> None:
    op.drop_table("billing_invoice_items")
    op.drop_index(op.f("ix_billing_invoices_invoice_number"), table_name="billing_invoices")
    op.drop_table("billing_invoices")
    op.drop_index(op.f("ix_billing_services_service_code"), table_name="billing_services")
    op.drop_table("billing_services")
