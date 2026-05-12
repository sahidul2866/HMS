"""Add hospital-grade IPD workflow tables.

Revision ID: 20260511_0047
Revises: 20260509_0046
Create Date: 2026-05-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0047"
down_revision = "20260509_0046"
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


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def upgrade() -> None:
    for column in [
        sa.Column("assigned_nurse_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admission_source", sa.String(40), nullable=True),
        sa.Column("department_name", sa.String(120), nullable=True),
        sa.Column("payment_type", sa.String(60), nullable=True),
        sa.Column("insurance_info", sa.Text(), nullable=True),
        sa.Column("patient_condition", sa.Text(), nullable=True),
        sa.Column("billing_status", sa.String(40), nullable=False, server_default="unbilled"),
        sa.Column("discharge_status", sa.String(40), nullable=False, server_default="not_planned"),
        sa.Column("pharmacy_clearance_status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("lab_clearance_status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("radiology_clearance_status", sa.String(40), nullable=False, server_default="pending"),
    ]:
        _add_column("ipd_admissions", column)

    if not _has_table("ipd_staff_assignments"):
        op.create_table(
            "ipd_staff_assignments",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("staff_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("staff_name", sa.String(150), nullable=False),
            sa.Column("role_type", sa.String(40), nullable=False),
            sa.Column("assignment_type", sa.String(60), nullable=False, server_default="primary"),
            sa.Column("shift_name", sa.String(80), nullable=True),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("ipd_clinical_notes"):
        op.create_table(
            "ipd_clinical_notes",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("note_type", sa.String(60), nullable=False, server_default="progress_note"),
            sa.Column("title", sa.String(160), nullable=True),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("diagnosis", sa.Text(), nullable=True),
            sa.Column("treatment_plan", sa.Text(), nullable=True),
            sa.Column("template_key", sa.String(120), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("authored_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("authored_at", sa.DateTime(timezone=True), nullable=False),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["authored_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("ipd_nursing_notes"):
        op.create_table(
            "ipd_nursing_notes",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("note_type", sa.String(60), nullable=False, server_default="nursing_note"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("temperature", sa.Numeric(5, 2), nullable=True),
            sa.Column("pulse", sa.Integer(), nullable=True),
            sa.Column("respiratory_rate", sa.Integer(), nullable=True),
            sa.Column("systolic_bp", sa.Integer(), nullable=True),
            sa.Column("diastolic_bp", sa.Integer(), nullable=True),
            sa.Column("spo2", sa.Integer(), nullable=True),
            sa.Column("pain_score", sa.Integer(), nullable=True),
            sa.Column("intake_ml", sa.Numeric(10, 2), nullable=True),
            sa.Column("output_ml", sa.Numeric(10, 2), nullable=True),
            sa.Column("fall_risk", sa.String(40), nullable=True),
            sa.Column("abnormal_alert", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("ipd_orders"):
        op.create_table(
            "ipd_orders",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_type", sa.String(40), nullable=False),
            sa.Column("service_area", sa.String(40), nullable=True),
            sa.Column("item_name", sa.String(180), nullable=False),
            sa.Column("instructions", sa.Text(), nullable=True),
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
            sa.Column("priority", sa.String(40), nullable=False, server_default="routine"),
            sa.Column("status", sa.String(40), nullable=False, server_default="ordered"),
            sa.Column("billing_status", sa.String(40), nullable=False, server_default="unbilled"),
            sa.Column("ordered_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["ordered_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("ipd_medication_administrations"):
        op.create_table(
            "ipd_medication_administrations",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("medicine_name", sa.String(180), nullable=False),
            sa.Column("dose", sa.String(80), nullable=True),
            sa.Column("route", sa.String(80), nullable=True),
            sa.Column("frequency", sa.String(80), nullable=True),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("administered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="due"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("administered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["ipd_orders.id"]),
            sa.ForeignKeyConstraint(["administered_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("ipd_handovers"):
        op.create_table(
            "ipd_handovers",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("handover_type", sa.String(40), nullable=False, server_default="nursing"),
            sa.Column("shift_name", sa.String(80), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("pending_items", sa.Text(), nullable=True),
            sa.Column("precautions", sa.Text(), nullable=True),
            sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("receiver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("handed_over_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="pending_ack"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["receiver_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("ipd_timeline_events"):
        op.create_table(
            "ipd_timeline_events",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("source_type", sa.String(80), nullable=True),
            sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    for table in (
        "ipd_timeline_events",
        "ipd_handovers",
        "ipd_medication_administrations",
        "ipd_orders",
        "ipd_nursing_notes",
        "ipd_clinical_notes",
        "ipd_staff_assignments",
    ):
        if _has_table(table):
            op.drop_table(table)
    for column in (
        "radiology_clearance_status",
        "lab_clearance_status",
        "pharmacy_clearance_status",
        "discharge_status",
        "billing_status",
        "patient_condition",
        "insurance_info",
        "payment_type",
        "department_name",
        "admission_source",
        "assigned_nurse_user_id",
    ):
        if _has_column("ipd_admissions", column):
            op.drop_column("ipd_admissions", column)
