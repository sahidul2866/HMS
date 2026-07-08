from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class TelemedicineAppointment(Base, BaseModelMixin):
    __tablename__ = "telemedicine_appointments"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    appointment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("appointments.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    department_name: Mapped[str | None] = mapped_column(String(120), index=True)
    doctor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    telemedicine_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consultation_reason: Mapped[str | None] = mapped_column(Text)
    visit_type: Mapped[str] = mapped_column(String(40), nullable=False, default="new")
    appointment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="video")
    contact_phone: Mapped[str | None] = mapped_column(String(60))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    uploaded_files: Mapped[list | None] = mapped_column(JSON)
    queue_number: Mapped[str | None] = mapped_column(String(40), index=True)
    estimated_wait_minutes: Mapped[int | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="scheduled", index=True)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    consent_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    consent_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_by: Mapped[str | None] = mapped_column(String(160))
    consent_terms_version: Mapped[str | None] = mapped_column(String(60))
    video_provider: Mapped[str | None] = mapped_column(String(80))
    meeting_id: Mapped[str | None] = mapped_column(String(160), unique=True)
    join_url: Mapped[str | None] = mapped_column(Text)
    doctor_join_url: Mapped[str | None] = mapped_column(Text)
    booked_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    appointment = relationship("Appointment")
    patient = relationship("Patient")
    department = relationship("Department")
    doctor = relationship("User", foreign_keys=[doctor_user_id])
    booked_by = relationship("User", foreign_keys=[booked_by_user_id])
    billing_invoice = relationship("BillingInvoice")


class TelemedicineConsultation(Base, BaseModelMixin):
    __tablename__ = "telemedicine_consultations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    telemedicine_appointment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("telemedicine_appointments.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    doctor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    opd_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    doctor_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connection_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_connected")
    media_status: Mapped[dict | None] = mapped_column(JSON)
    current_complaint: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    prescription_text: Mapped[str | None] = mapped_column(Text)
    advice: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    follow_up_plan: Mapped[str | None] = mapped_column(Text)
    referral_department: Mapped[str | None] = mapped_column(String(120))
    referral_doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="ready_to_join", index=True)
    prescription_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    completed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    telemedicine_appointment = relationship("TelemedicineAppointment")
    patient = relationship("Patient")
    doctor = relationship("User", foreign_keys=[doctor_user_id])
    opd_visit = relationship("OPDVisit")
    referral_doctor = relationship("User", foreign_keys=[referral_doctor_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])


class TelemedicineChatMessage(Base, BaseModelMixin):
    __tablename__ = "telemedicine_chat_messages"

    consultation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("telemedicine_consultations.id"), nullable=False, index=True)
    sender_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    sender_patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    sender_role: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(40), nullable=False, default="text")
    attachment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("telemedicine_files.id"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    consultation = relationship("TelemedicineConsultation")
    sender_user = relationship("User")
    sender_patient = relationship("Patient")
    attachment = relationship("TelemedicineFile", foreign_keys=[attachment_id])


class TelemedicineFile(Base, BaseModelMixin):
    __tablename__ = "telemedicine_files"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    telemedicine_appointment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("telemedicine_appointments.id"), index=True)
    consultation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("telemedicine_consultations.id"), index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    file_category: Mapped[str] = mapped_column(String(80), nullable=False, default="medical_document")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="accepted")
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    appointment = relationship("TelemedicineAppointment")
    consultation = relationship("TelemedicineConsultation")
    patient = relationship("Patient")
    uploaded_by = relationship("User")


class TelemedicineInvestigationOrder(Base, BaseModelMixin):
    __tablename__ = "telemedicine_investigation_orders"

    consultation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("telemedicine_consultations.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    service_area: Mapped[str] = mapped_column(String(40), nullable=False)
    item_name: Mapped[str] = mapped_column(String(180), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    lab_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"))
    radiology_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_orders.id"))
    billing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ordered")

    consultation = relationship("TelemedicineConsultation")
    patient = relationship("Patient")
    lab_order = relationship("LabOrder")
    radiology_order = relationship("RadiologyOrder")


class TelemedicineSetting(Base, BaseModelMixin):
    __tablename__ = "telemedicine_settings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON)

    branch = relationship("Branch")
