"""add opd and ipd encounter modules

Revision ID: 20260320_0005
Revises: 20260320_0004
Create Date: 2026-03-20 16:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0005"
down_revision = "20260320_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opd_visits",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_number", sa.String(length=50), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("department_name", sa.String(length=120), nullable=False),
        sa.Column("consulting_doctor_name", sa.String(length=150), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="waiting"),
        sa.Column("consultation_fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("registered_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["registered_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opd_visits_visit_number"), "opd_visits", ["visit_number"], unique=True)

    op.create_table(
        "ipd_admissions",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admission_number", sa.String(length=50), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admission_type", sa.String(length=30), nullable=False, server_default="general"),
        sa.Column("ward_name", sa.String(length=120), nullable=False),
        sa.Column("bed_number", sa.String(length=60), nullable=False),
        sa.Column("attending_doctor_name", sa.String(length=150), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("daily_charge", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("advance_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="admitted"),
        sa.Column("expected_discharge_date", sa.Date(), nullable=True),
        sa.Column("discharged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discharge_note", sa.Text(), nullable=True),
        sa.Column("discharged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["admitted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["discharged_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ipd_admissions_admission_number"), "ipd_admissions", ["admission_number"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_ipd_admissions_admission_number"), table_name="ipd_admissions")
    op.drop_table("ipd_admissions")
    op.drop_index(op.f("ix_opd_visits_visit_number"), table_name="opd_visits")
    op.drop_table("opd_visits")
