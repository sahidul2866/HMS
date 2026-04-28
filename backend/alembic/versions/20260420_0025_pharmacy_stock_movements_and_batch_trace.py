"""add pharmacy stock movement ledger and sale batch tracing

Revision ID: 20260420_0025
Revises: 20260419_0024
Create Date: 2026-04-20 11:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260420_0025"
down_revision = "20260419_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pharmacy_sale_items", sa.Column("batch_no", sa.String(length=80), nullable=True))
    op.add_column("pharmacy_sale_items", sa.Column("expiry_date", sa.Date(), nullable=True))

    op.add_column("pharmacy_sale_returns", sa.Column("batch_no", sa.String(length=80), nullable=True))
    op.add_column("pharmacy_sale_returns", sa.Column("expiry_date", sa.Date(), nullable=True))

    op.create_table(
        "pharmacy_stock_movements",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(length=50), nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity_change", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("stock_before", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("stock_after", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("batch_no", sa.String(length=80), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["medicine_id"], ["pharmacy_medicines.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pharmacy_stock_movements_medicine_id", "pharmacy_stock_movements", ["medicine_id"])
    op.create_index("ix_pharmacy_stock_movements_reference_type", "pharmacy_stock_movements", ["reference_type"])
    op.create_index("ix_pharmacy_stock_movements_reference_id", "pharmacy_stock_movements", ["reference_id"])


def downgrade() -> None:
    op.drop_index("ix_pharmacy_stock_movements_reference_id", table_name="pharmacy_stock_movements")
    op.drop_index("ix_pharmacy_stock_movements_reference_type", table_name="pharmacy_stock_movements")
    op.drop_index("ix_pharmacy_stock_movements_medicine_id", table_name="pharmacy_stock_movements")
    op.drop_table("pharmacy_stock_movements")

    op.drop_column("pharmacy_sale_returns", "expiry_date")
    op.drop_column("pharmacy_sale_returns", "batch_no")

    op.drop_column("pharmacy_sale_items", "expiry_date")
    op.drop_column("pharmacy_sale_items", "batch_no")
