"""Add inventory stores, balances, requisitions and store-aware movements.

Revision ID: 20260506_0045
Revises: 20260504_0044
Create Date: 2026-05-06 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260506_0045"
down_revision = "20260504_0044"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    if not _has_table("inventory_stores"):
        op.create_table(
            "inventory_stores",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("parent_store_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("store_type", sa.String(60), nullable=False, server_default="sub_store"),
            sa.Column("department_name", sa.String(120), nullable=True),
            sa.Column("location", sa.String(160), nullable=True),
            sa.Column("allow_sub_store_transfers", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
            sa.ForeignKeyConstraint(["parent_store_id"], ["inventory_stores.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "code", name="uq_inventory_stores_branch_code"),
        )

    if not _has_table("inventory_store_items"):
        op.create_table(
            "inventory_store_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quantity_on_hand", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("reserved_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("reorder_level", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("minimum_stock_level", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("maximum_stock_level", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("location", sa.String(160), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["store_id"], ["inventory_stores.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("store_id", "item_id", name="uq_inventory_store_items_store_item"),
        )

    if not _has_table("inventory_requisitions"):
        op.create_table(
            "inventory_requisitions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_store_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("destination_store_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("department", sa.String(120), nullable=True),
            sa.Column("requested_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("approved_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("issued_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("priority", sa.String(40), nullable=False, server_default="normal"),
            sa.Column("required_date", sa.Date(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(60), nullable=False, server_default="draft"),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("rejected_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("issued_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_store_id"], ["inventory_stores.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["destination_store_id"], ["inventory_stores.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["rejected_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    for table_name in ("stock_batches", "stock_receivings", "stock_issues", "stock_adjustments", "inventory_stock_transactions"):
        _add_column(table_name, sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True))

    _add_column("stock_issues", sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add_column("stock_issues", sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True))

    for column_name in ("source_store_id", "destination_store_id", "requested_by", "approved_by", "issued_by", "received_by"):
        _add_column("stock_transfers", sa.Column(column_name, postgresql.UUID(as_uuid=True), nullable=True))
    for column_name in ("requested_quantity", "approved_quantity", "issued_quantity", "received_quantity"):
        _add_column("stock_transfers", sa.Column(column_name, sa.Numeric(14, 2), nullable=False, server_default="0"))
    for column_name in ("approved_at", "issued_at", "received_at"):
        _add_column("stock_transfers", sa.Column(column_name, sa.DateTime(timezone=True), nullable=True))

    _add_column("stock_adjustments", sa.Column("status", sa.String(60), nullable=False, server_default="posted"))
    _add_column("stock_adjustments", sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade():
    for table_name in ("inventory_requisitions", "inventory_store_items", "inventory_stores"):
        if _has_table(table_name):
            op.drop_table(table_name)
