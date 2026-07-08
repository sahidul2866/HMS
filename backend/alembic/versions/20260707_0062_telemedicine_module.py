"""Add telemedicine module."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260707_0062"
down_revision = "20260706_0061"
branch_labels = None
depends_on = None


def base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "telemedicine_appointments",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_name", sa.String(120), nullable=True),
        sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telemedicine_number", sa.String(80), nullable=False),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consultation_reason", sa.Text(), nullable=True),
        sa.Column("visit_type", sa.String(40), nullable=False),
        sa.Column("appointment_type", sa.String(40), nullable=False),
        sa.Column("contact_phone", sa.String(60), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("uploaded_files", sa.JSON(), nullable=True),
        sa.Column("queue_number", sa.String(40), nullable=True),
        sa.Column("estimated_wait_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("payment_status", sa.String(40), nullable=False),
        sa.Column("consultation_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consent_required", sa.Boolean(), nullable=False),
        sa.Column("consent_accepted", sa.Boolean(), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_by", sa.String(160), nullable=True),
        sa.Column("consent_terms_version", sa.String(60), nullable=True),
        sa.Column("video_provider", sa.String(80), nullable=True),
        sa.Column("meeting_id", sa.String(160), nullable=True),
        sa.Column("join_url", sa.Text(), nullable=True),
        sa.Column("doctor_join_url", sa.Text(), nullable=True),
        sa.Column("booked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["billing_invoice_id"], ["billing_invoices.id"]),
        sa.ForeignKeyConstraint(["booked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_id"),
        sa.UniqueConstraint("telemedicine_number"),
    )
    for column in ("patient_id", "doctor_user_id", "telemedicine_number", "appointment_at", "department_name", "queue_number", "status", "payment_status"):
        op.create_index(f"ix_telemedicine_appointments_{column}", "telemedicine_appointments", [column])

    op.create_table(
        "telemedicine_consultations",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("telemedicine_appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opd_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("patient_joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("doctor_joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_status", sa.String(40), nullable=False),
        sa.Column("media_status", sa.JSON(), nullable=True),
        sa.Column("current_complaint", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("prescription_text", sa.Text(), nullable=True),
        sa.Column("advice", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("follow_up_plan", sa.Text(), nullable=True),
        sa.Column("referral_department", sa.String(120), nullable=True),
        sa.Column("referral_doctor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("prescription_status", sa.String(40), nullable=False),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["opd_visit_id"], ["opd_visits.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["referral_doctor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["telemedicine_appointment_id"], ["telemedicine_appointments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("telemedicine_appointment_id", "patient_id", "doctor_user_id", "status"):
        op.create_index(f"ix_telemedicine_consultations_{column}", "telemedicine_consultations", [column])

    op.create_table(
        "telemedicine_files",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("telemedicine_appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consultation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_category", sa.String(80), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.String(40), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["consultation_id"], ["telemedicine_consultations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["telemedicine_appointment_id"], ["telemedicine_appointments.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("telemedicine_appointment_id", "consultation_id", "patient_id"):
        op.create_index(f"ix_telemedicine_files_{column}", "telemedicine_files", [column])

    op.create_table(
        "telemedicine_chat_messages",
        sa.Column("consultation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_role", sa.String(40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(40), nullable=False),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["attachment_id"], ["telemedicine_files.id"]),
        sa.ForeignKeyConstraint(["consultation_id"], ["telemedicine_consultations.id"]),
        sa.ForeignKeyConstraint(["sender_patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemedicine_chat_messages_consultation_id", "telemedicine_chat_messages", ["consultation_id"])

    op.create_table(
        "telemedicine_investigation_orders",
        sa.Column("consultation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_area", sa.String(40), nullable=False),
        sa.Column("item_name", sa.String(180), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("radiology_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("billing_status", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        *base_columns(),
        sa.ForeignKeyConstraint(["consultation_id"], ["telemedicine_consultations.id"]),
        sa.ForeignKeyConstraint(["lab_order_id"], ["lab_orders.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["radiology_order_id"], ["radiology_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemedicine_investigation_orders_consultation_id", "telemedicine_investigation_orders", ["consultation_id"])
    op.create_index("ix_telemedicine_investigation_orders_patient_id", "telemedicine_investigation_orders", ["patient_id"])

    op.create_table(
        "telemedicine_settings",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("setting_key", sa.String(120), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )


def downgrade() -> None:
    op.drop_table("telemedicine_settings")
    op.drop_table("telemedicine_investigation_orders")
    op.drop_table("telemedicine_chat_messages")
    op.drop_table("telemedicine_files")
    op.drop_table("telemedicine_consultations")
    op.drop_table("telemedicine_appointments")
