"""Add staff assistant settings.

Revision ID: 20260511_0053
Revises: 20260511_0052
Create Date: 2026-05-11 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0053"
down_revision = "20260511_0052"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade():
    if not _has_table("staff_bot_settings"):
        op.create_table(
            "staff_bot_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("setting_key", sa.String(120), nullable=False),
            sa.Column("setting_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "setting_key", name="uq_staff_bot_settings_branch_key"),
        )


def downgrade():
    if _has_table("staff_bot_settings"):
        op.drop_table("staff_bot_settings")
