"""add lab and radiology domain tables and billing links

Revision ID: 20260503_0040
Revises: 20260502_0039
Create Date: 2026-05-03 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260503_0040"
down_revision = "20260502_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Lab tables ---
    op.create_table(
        "lab_orders",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("er_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="routine"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["opd_visits.id"]),
        sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"]),
        sa.ForeignKeyConstraint(["er_visit_id"], ["er_visits.id"]),
        sa.ForeignKeyConstraint(["collected_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_orders_order_number", "lab_orders", ["order_number"], unique=False)

    op.create_table(
        "lab_order_items",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_name", sa.String(length=180), nullable=False),
        sa.Column("specimen_type", sa.String(length=60), nullable=True),
        sa.Column("specimen_instructions", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("reference_range_low", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference_range_high", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference_range_text", sa.String(length=180), nullable=True),
        sa.Column("unit", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ordered"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["order_id"], ["lab_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_order_items_order_id", "lab_order_items", ["order_id"], unique=False)

    op.create_table(
        "lab_results",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="preliminary"),
        sa.Column("overall_interpretation", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["order_id"], ["lab_orders.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_results_order_id", "lab_results", ["order_id"], unique=False)
    op.create_index("ix_lab_results_report_number", "lab_results", ["report_number"], unique=False)

    op.create_table(
        "lab_result_items",
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analyte_name", sa.String(length=150), nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        sa.Column("unit", sa.String(length=60), nullable=True),
        sa.Column("reference_range_low", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference_range_high", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference_range_text", sa.String(length=180), nullable=True),
        sa.Column("flag", sa.String(length=20), nullable=True),
        sa.Column("method", sa.String(length=120), nullable=True),
        sa.Column("instrument", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["result_id"], ["lab_results.id"]),
        sa.ForeignKeyConstraint(["order_item_id"], ["lab_order_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "lab_attachments",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["order_id"], ["lab_orders.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Radiology tables ---
    op.create_table(
        "radiology_orders",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("er_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("modality", sa.String(length=60), nullable=True),
        sa.Column("study_description", sa.String(length=255), nullable=False),
        sa.Column("body_part", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="routine"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["opd_visits.id"]),
        sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"]),
        sa.ForeignKeyConstraint(["er_visit_id"], ["er_visits.id"]),
        sa.ForeignKeyConstraint(["performed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_radiology_orders_order_number", "radiology_orders", ["order_number"], unique=False)

    op.create_table(
        "radiology_reports",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("overall_findings", sa.Text(), nullable=True),
        sa.Column("impression", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["order_id"], ["radiology_orders.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_radiology_reports_order_id", "radiology_reports", ["order_id"], unique=False)
    op.create_index("ix_radiology_reports_report_number", "radiology_reports", ["report_number"], unique=False)

    op.create_table(
        "radiology_report_sections",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_name", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["report_id"], ["radiology_reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "radiology_attachments",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["order_id"], ["radiology_orders.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["radiology_reports.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pacs_links",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("study_uid", sa.String(length=255), nullable=False),
        sa.Column("series_uid", sa.String(length=255), nullable=True),
        sa.Column("viewer_url", sa.Text(), nullable=True),
        sa.Column("pacs_provider", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="linked"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["order_id"], ["radiology_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Link OPD visit orders to new domain tables ---
    op.add_column("opd_visit_orders", sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_opd_visit_orders_lab_order_id_lab_orders",
        "opd_visit_orders",
        "lab_orders",
        ["lab_order_id"],
        ["id"],
    )

    op.add_column("opd_visit_orders", sa.Column("radiology_order_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_opd_visit_orders_radiology_order_id_radiology_orders",
        "opd_visit_orders",
        "radiology_orders",
        ["radiology_order_id"],
        ["id"],
    )

    # --- Billing item links ---
    op.create_table(
        "billing_item_links",
        sa.Column("invoice_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_module", sa.String(length=40), nullable=False),
        sa.Column("source_entity_type", sa.String(length=60), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["invoice_item_id"], ["billing_invoice_items.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_item_links_invoice_item_id", "billing_item_links", ["invoice_item_id"], unique=False)
    op.create_index("ix_billing_item_links_source", "billing_item_links", ["source_entity_type", "source_entity_id"], unique=False)
    op.create_index("ix_billing_item_links_branch_module", "billing_item_links", ["branch_id", "source_module"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_item_links_branch_module", table_name="billing_item_links")
    op.drop_index("ix_billing_item_links_source", table_name="billing_item_links")
    op.drop_index("ix_billing_item_links_invoice_item_id", table_name="billing_item_links")
    op.drop_table("billing_item_links")

    op.drop_constraint("fk_opd_visit_orders_radiology_order_id_radiology_orders", "opd_visit_orders", type_="foreignkey")
    op.drop_column("opd_visit_orders", "radiology_order_id")
    op.drop_constraint("fk_opd_visit_orders_lab_order_id_lab_orders", "opd_visit_orders", type_="foreignkey")
    op.drop_column("opd_visit_orders", "lab_order_id")

    op.drop_table("pacs_links")
    op.drop_table("radiology_attachments")
    op.drop_table("radiology_report_sections")
    op.drop_index("ix_radiology_reports_report_number", table_name="radiology_reports")
    op.drop_index("ix_radiology_reports_order_id", table_name="radiology_reports")
    op.drop_table("radiology_reports")
    op.drop_index("ix_radiology_orders_order_number", table_name="radiology_orders")
    op.drop_table("radiology_orders")

    op.drop_table("lab_attachments")
    op.drop_table("lab_result_items")
    op.drop_index("ix_lab_results_report_number", table_name="lab_results")
    op.drop_index("ix_lab_results_order_id", table_name="lab_results")
    op.drop_table("lab_results")
    op.drop_index("ix_lab_order_items_order_id", table_name="lab_order_items")
    op.drop_table("lab_order_items")
    op.drop_index("ix_lab_orders_order_number", table_name="lab_orders")
    op.drop_table("lab_orders")
