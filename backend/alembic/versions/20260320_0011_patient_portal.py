"""add patient portal user link and appointments

Revision ID: 20260320_0011
Revises: 20260320_0010
Create Date: 2026-03-20 23:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0011"
down_revision = "20260320_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_users_patient_id_patients", "users", "patients", ["patient_id"], ["id"])
    op.create_table(
        "appointments",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_number", sa.String(length=50), nullable=False),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="scheduled"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("booked_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["booked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_number"),
    )
    op.create_index("ix_appointments_appointment_number", "appointments", ["appointment_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_appointments_appointment_number", table_name="appointments")
    op.drop_table("appointments")
    op.drop_constraint("fk_users_patient_id_patients", "users", type_="foreignkey")
    op.drop_column("users", "patient_id")
