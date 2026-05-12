"""Add direct billing links to pharmacy dispenses.

Revision ID: 20260509_0046
Revises: 20260506_0045
Create Date: 2026-05-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260509_0046"
down_revision = "20260506_0045"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("pharmacy_dispenses", "billing_invoice_id"):
        op.add_column("pharmacy_dispenses", sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_pharm_disp_billing_invoice",
            "pharmacy_dispenses",
            "billing_invoices",
            ["billing_invoice_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_column("pharmacy_dispenses", "billing_invoice_item_id"):
        op.add_column("pharmacy_dispenses", sa.Column("billing_invoice_item_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_pharm_disp_billing_invoice_item",
            "pharmacy_dispenses",
            "billing_invoice_items",
            ["billing_invoice_item_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if _has_column("pharmacy_dispenses", "billing_invoice_item_id"):
        op.drop_constraint("fk_pharm_disp_billing_invoice_item", "pharmacy_dispenses", type_="foreignkey")
        op.drop_column("pharmacy_dispenses", "billing_invoice_item_id")
    if _has_column("pharmacy_dispenses", "billing_invoice_id"):
        op.drop_constraint("fk_pharm_disp_billing_invoice", "pharmacy_dispenses", type_="foreignkey")
        op.drop_column("pharmacy_dispenses", "billing_invoice_id")
