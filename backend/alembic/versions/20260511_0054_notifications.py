"""Add role based notification center.

Revision ID: 20260511_0054
Revises: 20260511_0053
Create Date: 2026-05-11 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0054"
down_revision = "20260511_0053"
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
    if not _has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("module", sa.String(60), nullable=False),
            sa.Column("priority", sa.String(24), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(32), nullable=False, server_default="unread"),
            sa.Column("notification_type", sa.String(32), nullable=False, server_default="instant"),
            sa.Column("source_key", sa.String(180), nullable=False),
            sa.Column("related_record_type", sa.String(80), nullable=True),
            sa.Column("related_record_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("related_display", sa.String(180), nullable=True),
            sa.Column("route", sa.String(240), nullable=True),
            sa.Column("action_label", sa.String(80), nullable=True),
            sa.Column("action_permission", sa.String(120), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("recipient_user_id", "source_key", name="uq_notifications_recipient_source"),
        )
        op.create_index("ix_notifications_inbox", "notifications", ["recipient_user_id", "status", "priority", "created_at"])
        op.create_index("ix_notifications_due", "notifications", ["recipient_user_id", "due_at", "status"])

    if not _has_table("notification_audit_logs"):
        op.create_table(
            "notification_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("action", sa.String(60), nullable=False),
            sa.Column("module", sa.String(60), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("notification_settings"):
        op.create_table(
            "notification_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("setting_key", sa.String(120), nullable=False),
            sa.Column("setting_value", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "setting_key", name="uq_notification_settings_branch_key"),
        )


def downgrade():
    for table_name in ("notification_settings", "notification_audit_logs", "notifications"):
        if _has_table(table_name):
            op.drop_table(table_name)
