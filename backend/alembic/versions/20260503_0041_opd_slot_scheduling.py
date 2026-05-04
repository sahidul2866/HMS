"""add opd slot schedules and unified doctor slot bookings

Revision ID: 20260503_0041
Revises: 20260503_0040
Create Date: 2026-05-03 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260503_0041"
down_revision = "20260503_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("slot_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opd_visits", sa.Column("slot_start_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "doctor_opd_schedules",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(length=5), nullable=False),
        sa.Column("end_time", sa.String(length=5), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_user_id", "weekday", name="uq_doctor_opd_schedule_day"),
    )

    op.create_table(
        "doctor_slot_bookings",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slot_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="appointment"),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opd_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="booked"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["opd_visit_id"], ["opd_visits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_user_id", "slot_start_at", name="uq_doctor_slot_start"),
    )
    op.create_index("ix_doctor_slot_bookings_doctor_start", "doctor_slot_bookings", ["doctor_user_id", "slot_start_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_doctor_slot_bookings_doctor_start", table_name="doctor_slot_bookings")
    op.drop_table("doctor_slot_bookings")
    op.drop_table("doctor_opd_schedules")
    op.drop_column("opd_visits", "slot_start_at")
    op.drop_column("appointments", "slot_start_at")
