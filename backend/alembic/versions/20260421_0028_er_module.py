"""create ER module tables

Revision ID: 20260421_0028
Revises: 20260420_0027
Create Date: 2026-04-21 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260421_0028"
down_revision = "20260420_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "er_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_number", sa.String(length=50), nullable=False),
        sa.Column("arrival_mode", sa.String(length=40), nullable=False, server_default=sa.text("'walk_in'")),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_reference", sa.String(length=120), nullable=True),
        sa.Column("emergency_contact_name", sa.String(length=120), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=20), nullable=True),
        sa.Column("triage_category", sa.String(length=30), nullable=False, server_default=sa.text("'yellow'")),
        sa.Column("triage_level", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("vitals", sa.Text(), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("initial_diagnosis", sa.Text(), nullable=True),
        sa.Column("assigned_doctor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_nurse_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_location", sa.String(length=120), nullable=True),
        sa.Column("treatment_status", sa.String(length=40), nullable=True, server_default=sa.text("'pending'")),
        sa.Column("treatment_notes", sa.Text(), nullable=True),
        sa.Column("disposition", sa.String(length=255), nullable=True),
        sa.Column("referral_hospital", sa.String(length=150), nullable=True),
        sa.Column("referral_doctor_name", sa.String(length=150), nullable=True),
        sa.Column("disposition_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'waiting'")),
        sa.Column("admitted_to_ipd_admission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discharged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name="fk_er_visits_branch_id"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_er_visits_patient_id"),
        sa.ForeignKeyConstraint(["assigned_doctor_user_id"], ["users.id"], name="fk_er_visits_assigned_doctor_user_id"),
        sa.ForeignKeyConstraint(["assigned_nurse_user_id"], ["users.id"], name="fk_er_visits_assigned_nurse_user_id"),
        sa.ForeignKeyConstraint(["admitted_to_ipd_admission_id"], ["ipd_admissions.id"], name="fk_er_visits_admitted_to_ipd_admission_id"),
    )
    op.create_index("ix_er_visits_visit_number", "er_visits", ["visit_number"], unique=True)

    op.create_table(
        "er_ambulance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("er_visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ambulance_service", sa.String(length=120), nullable=False),
        sa.Column("driver_name", sa.String(length=120), nullable=True),
        sa.Column("pickup_location", sa.String(length=255), nullable=True),
        sa.Column("drop_off_location", sa.String(length=255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["er_visit_id"], ["er_visits.id"], name="fk_er_ambulance_records_er_visit_id"),
    )


def downgrade() -> None:
    op.drop_table("er_ambulance_records")
    op.drop_index("ix_er_visits_visit_number", table_name="er_visits")
    op.drop_table("er_visits")
