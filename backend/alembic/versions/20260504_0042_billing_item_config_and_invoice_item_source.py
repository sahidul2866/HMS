"""billing item config and invoice source fields

Revision ID: 20260504_0042
Revises: 20260503_0041_opd_slot_scheduling
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260504_0042"
down_revision = "20260503_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_item_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_module", sa.String(length=40), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_code", sa.String(length=80), nullable=False),
        sa.Column("service_name", sa.String(length=180), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("room_number", sa.String(length=60), nullable=True),
        sa.Column("doctor_share_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("max_discount_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("max_discount_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("billing_instruction", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_module", "source_entity_id", name="uq_billing_item_configs_source"),
    )
    op.create_index("ix_billing_item_configs_source_module", "billing_item_configs", ["source_module"], unique=False)
    op.create_index("ix_billing_item_configs_source_entity_id", "billing_item_configs", ["source_entity_id"], unique=False)

    op.add_column("billing_invoice_items", sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("billing_invoice_items", sa.Column("billing_instruction", sa.Text(), nullable=True))
    op.alter_column("billing_invoice_items", "billing_service_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.alter_column("billing_invoice_items", "billing_service_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_column("billing_invoice_items", "billing_instruction")
    op.drop_column("billing_invoice_items", "source_entity_id")

    op.drop_index("ix_billing_item_configs_source_entity_id", table_name="billing_item_configs")
    op.drop_index("ix_billing_item_configs_source_module", table_name="billing_item_configs")
    op.drop_table("billing_item_configs")
