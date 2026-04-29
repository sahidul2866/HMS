"""Create inventory module tables.

Revision ID: 20260428_0030_inventory_module
Revises: 20260425_0029_billing_item_controls_and_rooms
Create Date: 2026-04-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260428_0030"
down_revision = "20260421_0028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_type", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_person", sa.String(150), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(120), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tax_number", sa.String(50), nullable=True),
        sa.Column("payment_terms", sa.String(200), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_code", sa.String(120), nullable=True),
        sa.Column("barcode", sa.String(150), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sub_category", sa.String(120), nullable=True),
        sa.Column("item_type", sa.String(80), nullable=False),
        sa.Column("unit_of_measurement", sa.String(50), nullable=False),
        sa.Column("is_batch_tracked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reorder_level", sa.Numeric(10, 2), nullable=True),
        sa.Column("minimum_stock_level", sa.Numeric(10, 2), nullable=True),
        sa.Column("maximum_stock_level", sa.Numeric(10, 2), nullable=True),
        sa.Column("storage_location", sa.String(200), nullable=True),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stock_quantity", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("stock_value", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["inventory_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stock_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_no", sa.String(120), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stock_receivings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_number", sa.String(120), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("department", sa.String(120), nullable=True),
        sa.Column("batch_no", sa.String(120), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stock_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department", sa.String(120), nullable=True),
        sa.Column("requestor", sa.String(150), nullable=True),
        sa.Column("purpose", sa.String(200), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["stock_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stock_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_location", sa.String(200), nullable=True),
        sa.Column("destination_location", sa.String(200), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(60), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["stock_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stock_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("adjustment_type", sa.String(60), nullable=False),
        sa.Column("quantity_change", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["stock_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inventory_stock_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(60), nullable=False),
        sa.Column("reference_type", sa.String(60), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity_change", sa.Numeric(15, 2), nullable=False),
        sa.Column("stock_before", sa.Numeric(15, 2), nullable=False),
        sa.Column("stock_after", sa.Numeric(15, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["stock_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "purchase_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department", sa.String(120), nullable=True),
        sa.Column("requested_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("priority", sa.String(40), nullable=True),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="requested"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reagents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reagent_code", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("test_mapping", sa.Text(), nullable=True),
        sa.Column("analyzer_mapping", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.String(150), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storage_condition", sa.String(80), nullable=True),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("opening_balance", sa.Numeric(10, 2), nullable=True),
        sa.Column("opened_balance", sa.Numeric(10, 2), nullable=True),
        sa.Column("closed_balance", sa.Numeric(10, 2), nullable=True),
        sa.Column("stability_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(60), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reagent_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reagent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_no", sa.String(120), nullable=True),
        sa.Column("lot_number", sa.String(120), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("quantity_received", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity_available", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity_opened", sa.Numeric(10, 2), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("stability_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(60), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reagent_id"], ["reagents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reagent_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reagent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analyzer_name", sa.String(150), nullable=True),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("quantity_used", sa.Numeric(10, 2), nullable=False),
        sa.Column("reagent_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["reagent_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reagent_id"], ["reagents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reagent_wastage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reagent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("wasted_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("status", sa.String(60), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["reagent_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reagent_id"], ["reagents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reagent_test_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reagent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reagent_id"], ["reagents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("reagent_test_mappings")
    op.drop_table("reagent_wastage")
    op.drop_table("reagent_usage")
    op.drop_table("reagent_batches")
    op.drop_table("reagents")
    op.drop_table("purchase_requests")
    op.drop_table("inventory_stock_transactions")
    op.drop_table("stock_adjustments")
    op.drop_table("stock_transfers")
    op.drop_table("stock_issues")
    op.drop_table("stock_receivings")
    op.drop_table("stock_batches")
    op.drop_table("inventory_items")
    op.drop_table("suppliers")
    op.drop_table("inventory_categories")
