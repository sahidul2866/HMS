from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class OTRoom(Base, BaseModelMixin):
    __tablename__ = "ot_rooms"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    room_type: Mapped[str] = mapped_column(String(60), nullable=False, default="major")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="available")
    floor: Mapped[str | None] = mapped_column(String(60))
    equipment_summary: Mapped[str | None] = mapped_column(Text)
    hourly_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)

    schedules = relationship("SurgerySchedule", back_populates="room")


class OTBooking(Base, BaseModelMixin):
    __tablename__ = "ot_bookings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    source_module: Mapped[str | None] = mapped_column(String(40))
    source_reference_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    booking_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    procedure_name: Mapped[str] = mapped_column(String(200), nullable=False)
    surgery_type: Mapped[str] = mapped_column(String(60), nullable=False, default="elective")
    priority_level: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    preferred_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(nullable=False, default=60)
    department_name: Mapped[str | None] = mapped_column(String(120))
    diagnosis: Mapped[str | None] = mapped_column(Text)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="requested")
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    patient = relationship("Patient")
    requested_by = relationship("User")
    schedule = relationship("SurgerySchedule", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class SurgerySchedule(Base, BaseModelMixin):
    __tablename__ = "surgery_schedules"
    __table_args__ = (UniqueConstraint("room_id", "scheduled_start_at", "scheduled_end_at", name="uq_ot_room_exact_slot"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ot_bookings.id"), nullable=False)
    room_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ot_rooms.id"), nullable=False)
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    primary_surgeon_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    assistant_surgeon_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    anesthetist_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    scrub_nurse_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    circulating_nurse_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    technician_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="scheduled")
    patient_shifted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    surgery_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    surgery_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    room_entry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    room_exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delay_reason: Mapped[str | None] = mapped_column(Text)

    booking = relationship("OTBooking", back_populates="schedule")
    room = relationship("OTRoom", back_populates="schedules")
    primary_surgeon = relationship("User", foreign_keys=[primary_surgeon_user_id])
    assistant_surgeon = relationship("User", foreign_keys=[assistant_surgeon_user_id])
    anesthetist = relationship("User", foreign_keys=[anesthetist_user_id])
    team_assignments = relationship("SurgeryTeamAssignment", back_populates="schedule", cascade="all, delete-orphan")
    pre_op_checklist = relationship("PreOpChecklist", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    anesthesia_record = relationship("AnesthesiaRecord", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    surgery_notes = relationship("SurgeryNote", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    recovery = relationship("PostOpRecovery", back_populates="schedule", uselist=False, cascade="all, delete-orphan")


class SurgeryTeamAssignment(Base, BaseModelMixin):
    __tablename__ = "surgery_team_assignments"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    staff_name: Mapped[str | None] = mapped_column(String(150))
    response_status: Mapped[str] = mapped_column(String(40), nullable=False, default="assigned")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    schedule = relationship("SurgerySchedule", back_populates="team_assignments")
    user = relationship("User")


class PreOpChecklist(Base, BaseModelMixin):
    __tablename__ = "pre_op_checklists"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False, unique=True)
    consent_signed: Mapped[bool] = mapped_column(default=False, nullable=False)
    anesthesia_cleared: Mapped[bool] = mapped_column(default=False, nullable=False)
    lab_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    radiology_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    blood_arranged: Mapped[bool] = mapped_column(default=False, nullable=False)
    npo_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    site_marked: Mapped[bool] = mapped_column(default=False, nullable=False)
    equipment_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    implant_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    allergy_info: Mapped[str | None] = mapped_column(Text)
    current_medication_review: Mapped[str | None] = mapped_column(Text)
    pre_op_diagnosis: Mapped[str | None] = mapped_column(Text)
    risk_assessment_notes: Mapped[str | None] = mapped_column(Text)
    ready_for_ot: Mapped[bool] = mapped_column(default=False, nullable=False)
    checked_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    schedule = relationship("SurgerySchedule", back_populates="pre_op_checklist")


class AnesthesiaRecord(Base, BaseModelMixin):
    __tablename__ = "anesthesia_records"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False, unique=True)
    anesthesia_type: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    pre_assessment: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    anesthesia_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anesthesia_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    medication_record: Mapped[str | None] = mapped_column(Text)
    fluid_record: Mapped[str | None] = mapped_column(Text)
    vitals_summary: Mapped[str | None] = mapped_column(Text)
    complications: Mapped[str | None] = mapped_column(Text)
    recovery_notes: Mapped[str | None] = mapped_column(Text)
    clearance_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    signed_off_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    schedule = relationship("SurgerySchedule", back_populates="anesthesia_record")


class SurgeryNote(Base, BaseModelMixin):
    __tablename__ = "surgery_notes"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False, unique=True)
    procedure_performed: Mapped[str | None] = mapped_column(Text)
    operative_findings: Mapped[str | None] = mapped_column(Text)
    surgeon_notes: Mapped[str | None] = mapped_column(Text)
    nursing_notes: Mapped[str | None] = mapped_column(Text)
    instrument_count_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    sponge_count_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    implant_usage_details: Mapped[str | None] = mapped_column(Text)
    specimen_collection_details: Mapped[str | None] = mapped_column(Text)
    surgery_outcome: Mapped[str] = mapped_column(String(80), nullable=False, default="successful")
    surgeon_signed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    anesthetist_signed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    nurse_signed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    schedule = relationship("SurgerySchedule", back_populates="surgery_notes")


class PostOpRecovery(Base, BaseModelMixin):
    __tablename__ = "post_op_recovery"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False, unique=True)
    transfer_to: Mapped[str] = mapped_column(String(80), nullable=False, default="recovery")
    recovery_admission_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vitals_summary: Mapped[str | None] = mapped_column(Text)
    pain_score: Mapped[int | None] = mapped_column()
    consciousness_status: Mapped[str | None] = mapped_column(String(120))
    post_op_instructions: Mapped[str | None] = mapped_column(Text)
    medication_instructions: Mapped[str | None] = mapped_column(Text)
    nursing_observations: Mapped[str | None] = mapped_column(Text)
    recovery_discharge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handover_notes: Mapped[str | None] = mapped_column(Text)
    complication_summary: Mapped[str | None] = mapped_column(Text)

    schedule = relationship("SurgerySchedule", back_populates="recovery")


class OTConsumableUsage(Base, BaseModelMixin):
    __tablename__ = "ot_consumable_usage"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False)
    inventory_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"))
    item_name: Mapped[str] = mapped_column(String(180), nullable=False)
    batch_no: Mapped[str | None] = mapped_column(String(100))
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    quantity_returned: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    wastage_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    charged_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)


class OTEquipmentUsage(Base, BaseModelMixin):
    __tablename__ = "ot_equipment_usage"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False)
    equipment_name: Mapped[str] = mapped_column(String(180), nullable=False)
    usage_notes: Mapped[str | None] = mapped_column(Text)
    charge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)


class OTBillingItem(Base, BaseModelMixin):
    __tablename__ = "ot_billing_items"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False)
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    charge_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")


class OTDocument(Base, BaseModelMixin):
    __tablename__ = "ot_documents"

    schedule_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("surgery_schedules.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="stored")


class OTAuditLog(Base, BaseModelMixin):
    __tablename__ = "ot_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[str | None] = mapped_column(Text)
