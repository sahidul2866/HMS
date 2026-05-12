"""Add global barcode and QR scanner registry.

Revision ID: 20260511_0052
Revises: 20260511_0051
Create Date: 2026-05-11 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0052"
down_revision = "20260511_0051"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _common_columns():
    return [
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade():
    if not _has_table("scan_codes"):
        op.create_table(
            "scan_codes",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("code_value", sa.String(180), nullable=False),
            sa.Column("code_type", sa.String(40), nullable=False, server_default="qr"),
            sa.Column("purpose", sa.String(80), nullable=False),
            sa.Column("record_type", sa.String(80), nullable=False),
            sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("display_value", sa.String(180), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code_value", name="uq_scan_codes_code_value"),
        )
        op.create_index("ix_scan_codes_record", "scan_codes", ["record_type", "record_id"])

    if not _has_table("scan_settings"):
        op.create_table(
            "scan_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("setting_key", sa.String(120), nullable=False),
            sa.Column("setting_value", sa.JSON(), nullable=False),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "department_id", "setting_key", name="uq_scan_settings_scope_key"),
        )

    if not _has_table("scan_events"):
        op.create_table(
            "scan_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("scanned_code", sa.String(220), nullable=False),
            sa.Column("normalized_code", sa.String(220), nullable=False),
            sa.Column("module", sa.String(80), nullable=True),
            sa.Column("action", sa.String(80), nullable=True),
            sa.Column("record_type", sa.String(80), nullable=True),
            sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("success", sa.String(20), nullable=False, server_default="false"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("device_label", sa.String(160), nullable=True),
            sa.Column("location_label", sa.String(160), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_scan_events_lookup", "scan_events", ["normalized_code", "record_type", "created_at"])


def downgrade():
    for table_name in ("scan_events", "scan_settings", "scan_codes"):
        if _has_table(table_name):
            op.drop_table(table_name)

