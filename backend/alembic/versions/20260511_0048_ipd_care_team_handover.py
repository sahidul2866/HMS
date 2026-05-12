"""Add IPD care team schedule and structured handover fields.

Revision ID: 20260511_0048
Revises: 20260511_0047
Create Date: 2026-05-11 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0048"
down_revision = "20260511_0047"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    for column in [
        sa.Column("ward_name", sa.String(120), nullable=True),
        sa.Column("bed_number", sa.String(60), nullable=True),
        sa.Column("department_name", sa.String(120), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("schedule_status", sa.String(60), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    ]:
        _add_column("ipd_staff_assignments", column)

    for column in [
        sa.Column("patient_condition", sa.Text(), nullable=True),
        sa.Column("active_diagnosis", sa.Text(), nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("pending_orders", sa.Text(), nullable=True),
        sa.Column("medication_due", sa.Text(), nullable=True),
        sa.Column("abnormal_vitals", sa.Text(), nullable=True),
        sa.Column("critical_alerts", sa.Text(), nullable=True),
        sa.Column("discharge_tasks", sa.Text(), nullable=True),
        sa.Column("special_instructions", sa.Text(), nullable=True),
    ]:
        _add_column("ipd_handovers", column)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("ipd_staff_assignments")}
    if "fk_ipd_staff_assignments_changed_by_users" not in existing_fks and _has_column("ipd_staff_assignments", "changed_by_user_id"):
        op.create_foreign_key(
            "fk_ipd_staff_assignments_changed_by_users",
            "ipd_staff_assignments",
            "users",
            ["changed_by_user_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("ipd_staff_assignments")}
    if "fk_ipd_staff_assignments_changed_by_users" in existing_fks:
        op.drop_constraint("fk_ipd_staff_assignments_changed_by_users", "ipd_staff_assignments", type_="foreignkey")

    for column_name in [
        "special_instructions",
        "discharge_tasks",
        "critical_alerts",
        "abnormal_vitals",
        "medication_due",
        "pending_orders",
        "treatment_plan",
        "active_diagnosis",
        "patient_condition",
    ]:
        _drop_column("ipd_handovers", column_name)

    for column_name in [
        "changed_by_user_id",
        "schedule_status",
        "override_reason",
        "changed_at",
        "department_name",
        "bed_number",
        "ward_name",
    ]:
        _drop_column("ipd_staff_assignments", column_name)
