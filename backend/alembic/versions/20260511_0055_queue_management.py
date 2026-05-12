"""Add hospital queue management.

Revision ID: 20260511_0055
Revises: 20260511_0054
Create Date: 2026-05-11 19:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0055"
down_revision = "20260511_0054"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _common_columns():
    return [
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade():
    if _has_table("opd_visits"):
        with op.batch_alter_table("opd_visits") as batch:
            if not _has_column("opd_visits", "queue_number"):
                batch.add_column(sa.Column("queue_number", sa.String(40), nullable=True))
            if not _has_column("opd_visits", "queue_status"):
                batch.add_column(sa.Column("queue_status", sa.String(40), nullable=True))
            if not _has_column("opd_visits", "queue_called_at"):
                batch.add_column(sa.Column("queue_called_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_table("queue_counters"):
        op.create_table(
            "queue_counters",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("code", sa.String(60), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("module", sa.String(60), nullable=False),
            sa.Column("service_area", sa.String(80), nullable=True),
            sa.Column("department_name", sa.String(120), nullable=True),
            sa.Column("room_number", sa.String(60), nullable=True),
            sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("audio_enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("display_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("current_token_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "code", name="uq_queue_counters_branch_code"),
        )

    if not _has_table("queue_tokens"):
        op.create_table(
            "queue_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("token_number", sa.String(40), nullable=False),
            sa.Column("token_sequence", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("token_date", sa.Date(), nullable=False),
            sa.Column("queue_scope", sa.String(60), nullable=False),
            sa.Column("module", sa.String(60), nullable=False),
            sa.Column("service_area", sa.String(80), nullable=True),
            sa.Column("department_name", sa.String(120), nullable=True),
            sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("counter_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("patient_label", sa.String(180), nullable=True),
            sa.Column("priority", sa.String(30), nullable=False, server_default="normal"),
            sa.Column("status", sa.String(40), nullable=False, server_default="waiting"),
            sa.Column("source_type", sa.String(80), nullable=False),
            sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("blood_request_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("recalled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["counter_id"], ["queue_counters.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["visit_id"], ["opd_visits.id"]),
            sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
            sa.ForeignKeyConstraint(["invoice_id"], ["billing_invoices.id"]),
            sa.ForeignKeyConstraint(["blood_request_id"], ["blood_requests.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "queue_scope", "token_date", "token_number", name="uq_queue_tokens_scope_number"),
            sa.UniqueConstraint("queue_scope", "source_type", "source_id", name="uq_queue_tokens_scope_source"),
        )
        op.create_index("ix_queue_tokens_worklist", "queue_tokens", ["queue_scope", "status", "priority", "created_at"])
        op.create_foreign_key("fk_queue_counters_current_token_id_queue_tokens", "queue_counters", "queue_tokens", ["current_token_id"], ["id"])

    if not _has_table("queue_audit_logs"):
        op.create_table(
            "queue_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("token_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("counter_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("module", sa.String(60), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["token_id"], ["queue_tokens.id"]),
            sa.ForeignKeyConstraint(["counter_id"], ["queue_counters.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("queue_settings"):
        op.create_table(
            "queue_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("setting_key", sa.String(120), nullable=False),
            sa.Column("setting_value", sa.JSON(), nullable=False, server_default="{}"),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "setting_key", name="uq_queue_settings_branch_key"),
        )


def downgrade():
    for table_name in ("queue_settings", "queue_audit_logs", "queue_tokens", "queue_counters"):
        if _has_table(table_name):
            op.drop_table(table_name)
    if _has_table("opd_visits"):
        with op.batch_alter_table("opd_visits") as batch:
            for column_name in ("queue_called_at", "queue_status", "queue_number"):
                if _has_column("opd_visits", column_name):
                    batch.drop_column(column_name)
