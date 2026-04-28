"""add cross-module billing, pharmacy, and investigation linkage fields

Revision ID: 20260420_0027
Revises: 20260420_0026
Create Date: 2026-04-20 20:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260420_0027"
down_revision = "20260420_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_invoices", sa.Column("source_opd_visit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("billing_invoices", sa.Column("source_ipd_admission_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("billing_invoices", sa.Column("source_module", sa.String(length=40), nullable=True))
    op.add_column("billing_invoices", sa.Column("billing_stage", sa.String(length=40), nullable=True))
    op.create_foreign_key("fk_billing_invoices_source_opd_visit_id", "billing_invoices", "opd_visits", ["source_opd_visit_id"], ["id"])
    op.create_foreign_key("fk_billing_invoices_source_ipd_admission_id", "billing_invoices", "ipd_admissions", ["source_ipd_admission_id"], ["id"])

    op.add_column("billing_invoice_items", sa.Column("source_opd_visit_order_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("billing_invoice_items", sa.Column("source_label", sa.String(length=180), nullable=True))
    op.add_column("billing_invoice_items", sa.Column("source_module", sa.String(length=40), nullable=True))
    op.create_foreign_key("fk_billing_invoice_items_source_opd_visit_order_id", "billing_invoice_items", "opd_visit_orders", ["source_opd_visit_order_id"], ["id"])

    op.add_column("pharmacy_sales", sa.Column("source_visit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_pharmacy_sales_source_visit_id", "pharmacy_sales", "opd_visits", ["source_visit_id"], ["id"])

    op.add_column("pharmacy_sale_items", sa.Column("source_visit_order_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_pharmacy_sale_items_source_visit_order_id", "pharmacy_sale_items", "opd_visit_orders", ["source_visit_order_id"], ["id"])

    op.add_column("pharmacy_investigations", sa.Column("source_visit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_pharmacy_investigations_source_visit_id", "pharmacy_investigations", "opd_visits", ["source_visit_id"], ["id"])

    op.add_column("pharmacy_investigation_items", sa.Column("source_visit_order_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_pharmacy_investigation_items_source_visit_order_id", "pharmacy_investigation_items", "opd_visit_orders", ["source_visit_order_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_pharmacy_investigation_items_source_visit_order_id", "pharmacy_investigation_items", type_="foreignkey")
    op.drop_column("pharmacy_investigation_items", "source_visit_order_id")

    op.drop_constraint("fk_pharmacy_investigations_source_visit_id", "pharmacy_investigations", type_="foreignkey")
    op.drop_column("pharmacy_investigations", "source_visit_id")

    op.drop_constraint("fk_pharmacy_sale_items_source_visit_order_id", "pharmacy_sale_items", type_="foreignkey")
    op.drop_column("pharmacy_sale_items", "source_visit_order_id")

    op.drop_constraint("fk_pharmacy_sales_source_visit_id", "pharmacy_sales", type_="foreignkey")
    op.drop_column("pharmacy_sales", "source_visit_id")

    op.drop_constraint("fk_billing_invoice_items_source_opd_visit_order_id", "billing_invoice_items", type_="foreignkey")
    op.drop_column("billing_invoice_items", "source_module")
    op.drop_column("billing_invoice_items", "source_label")
    op.drop_column("billing_invoice_items", "source_opd_visit_order_id")

    op.drop_constraint("fk_billing_invoices_source_ipd_admission_id", "billing_invoices", type_="foreignkey")
    op.drop_constraint("fk_billing_invoices_source_opd_visit_id", "billing_invoices", type_="foreignkey")
    op.drop_column("billing_invoices", "billing_stage")
    op.drop_column("billing_invoices", "source_module")
    op.drop_column("billing_invoices", "source_ipd_admission_id")
    op.drop_column("billing_invoices", "source_opd_visit_id")
