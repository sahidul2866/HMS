"""extend investigation settings and add order items

Revision ID: 20260420_0026
Revises: 20260420_0025
Create Date: 2026-04-20 14:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260420_0026"
down_revision = "20260420_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pharmacy_investigation_settings", sa.Column("normal_range", sa.String(length=180), nullable=True))
    op.add_column("pharmacy_investigation_settings", sa.Column("unit", sa.String(length=60), nullable=True))
    op.add_column("pharmacy_investigation_settings", sa.Column("description", sa.Text(), nullable=True))

    op.add_column("pharmacy_investigations", sa.Column("report_title", sa.String(length=180), nullable=True))
    op.add_column("pharmacy_investigations", sa.Column("report_footer_note", sa.Text(), nullable=True))
    op.add_column("pharmacy_investigations", sa.Column("printable_schema", sa.Text(), nullable=True))

    op.create_table(
        "pharmacy_investigation_items",
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ordered"),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("normal_range_snapshot", sa.String(length=180), nullable=True),
        sa.Column("unit_snapshot", sa.String(length=60), nullable=True),
        sa.Column("description_snapshot", sa.Text(), nullable=True),
        sa.Column("report_header_snapshot", sa.Text(), nullable=True),
        sa.Column("report_template_snapshot", sa.Text(), nullable=True),
        sa.Column("report_note_template_snapshot", sa.Text(), nullable=True),
        sa.Column("requires_report", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["pharmacy_investigations.id"]),
        sa.ForeignKeyConstraint(["setting_id"], ["pharmacy_investigation_settings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pharmacy_investigation_items_investigation_id", "pharmacy_investigation_items", ["investigation_id"])


def downgrade() -> None:
    op.drop_index("ix_pharmacy_investigation_items_investigation_id", table_name="pharmacy_investigation_items")
    op.drop_table("pharmacy_investigation_items")

    op.drop_column("pharmacy_investigations", "printable_schema")
    op.drop_column("pharmacy_investigations", "report_footer_note")
    op.drop_column("pharmacy_investigations", "report_title")

    op.drop_column("pharmacy_investigation_settings", "description")
    op.drop_column("pharmacy_investigation_settings", "unit")
    op.drop_column("pharmacy_investigation_settings", "normal_range")
