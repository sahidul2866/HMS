"""drop legacy billing services table

Revision ID: 20260504_0043
Revises: 20260504_0042
Create Date: 2026-05-04
"""

from alembic import op


revision = "20260504_0043"
down_revision = "20260504_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_billing_invoice_items_billing_service_id_billing_services",
        "billing_invoice_items",
        type_="foreignkey",
    )
    op.drop_column("billing_invoice_items", "billing_service_id")
    op.drop_index("ix_billing_services_service_code", table_name="billing_services")
    op.drop_table("billing_services")


def downgrade() -> None:
    raise RuntimeError("Downgrade for dropping legacy billing_services is not supported.")
