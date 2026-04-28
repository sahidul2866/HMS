"""billing item controls and investigation rooms

Revision ID: 20260425_0029
Revises: 20260425_0028
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260425_0029"
down_revision = "20260425_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_settings", sa.Column("default_referral_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("billing_settings", sa.Column("max_item_discount_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("billing_settings", sa.Column("max_invoice_discount_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("billing_services", sa.Column("max_discount_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("billing_services", sa.Column("max_discount_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("billing_services", sa.Column("room_number", sa.String(length=60), nullable=True))
    op.add_column("billing_invoice_items", sa.Column("max_discount_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("billing_invoice_items", sa.Column("max_discount_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("billing_invoice_items", sa.Column("room_number", sa.String(length=60), nullable=True))
    op.add_column("pharmacy_investigation_settings", sa.Column("room_number", sa.String(length=60), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("room_number", sa.String(length=60), nullable=True))


def downgrade() -> None:
    op.drop_column("opd_visit_orders", "room_number")
    op.drop_column("pharmacy_investigation_settings", "room_number")
    op.drop_column("billing_invoice_items", "room_number")
    op.drop_column("billing_invoice_items", "max_discount_amount")
    op.drop_column("billing_invoice_items", "max_discount_percentage")
    op.drop_column("billing_services", "room_number")
    op.drop_column("billing_services", "max_discount_amount")
    op.drop_column("billing_services", "max_discount_percentage")
    op.drop_column("billing_settings", "max_invoice_discount_amount")
    op.drop_column("billing_settings", "max_item_discount_amount")
    op.drop_column("billing_settings", "default_referral_percentage")
