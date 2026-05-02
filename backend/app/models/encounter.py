from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class IPDBed(Base, BaseModelMixin):
    __tablename__ = "ipd_beds"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    ward_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bed_number: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    bed_type: Mapped[str] = mapped_column(String(40), nullable=False, default="general")
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="available")
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    admissions = relationship("IPDAdmission", back_populates="bed")


class OPDVisit(Base, BaseModelMixin):
    __tablename__ = "opd_visits"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    source_appointment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("appointments.id"))
    consulting_doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    converted_ipd_admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    visit_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_name: Mapped[str] = mapped_column(String(120), nullable=False)
    consulting_doctor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    visit_type: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    history_of_present_illness: Mapped[str | None] = mapped_column(Text)
    past_history: Mapped[str | None] = mapped_column(Text)
    vital_signs: Mapped[str | None] = mapped_column(Text)
    examination_note: Mapped[str | None] = mapped_column(Text)
    provisional_diagnosis: Mapped[str | None] = mapped_column(Text)
    final_diagnosis: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    follow_up_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="waiting")
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    consultation_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    consultation_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    consultation_payment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unpaid")
    consultation_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    registered_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    patient = relationship("Patient")
    source_appointment = relationship("Appointment", back_populates="opd_visits")
    registered_by = relationship("User", foreign_keys=[registered_by_user_id])
    consulting_doctor = relationship("User", foreign_keys=[consulting_doctor_user_id])
    converted_ipd_admission = relationship("IPDAdmission", foreign_keys=[converted_ipd_admission_id])
    orders = relationship("OPDVisitOrder", back_populates="visit", cascade="all, delete-orphan")


class OPDVisitOrder(Base, BaseModelMixin):
    __tablename__ = "opd_visit_orders"

    visit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"), nullable=False)
    order_type: Mapped[str] = mapped_column(String(30), nullable=False)
    service_area: Mapped[str | None] = mapped_column(String(30))
    item_name: Mapped[str] = mapped_column(String(180), nullable=False)
    room_number: Mapped[str | None] = mapped_column(String(60))
    instructions: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    result_text: Mapped[str | None] = mapped_column(Text)
    sample_note: Mapped[str | None] = mapped_column(Text)
    sample_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sample_collected_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    visit = relationship("OPDVisit", back_populates="orders")
    sample_collected_by = relationship("User", foreign_keys=[sample_collected_by_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])


class IPDAdmission(Base, BaseModelMixin):
    __tablename__ = "ipd_admissions"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    bed_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_beds.id"))
    attending_doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    admission_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    admission_type: Mapped[str] = mapped_column(String(30), nullable=False, default="general")
    ward_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bed_number: Mapped[str] = mapped_column(String(60), nullable=False)
    attending_doctor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    daily_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="admitted")
    expected_discharge_date: Mapped[date | None] = mapped_column(Date)
    discharged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discharge_condition: Mapped[str | None] = mapped_column(String(120))
    discharge_diagnosis: Mapped[str | None] = mapped_column(Text)
    discharge_summary: Mapped[str | None] = mapped_column(Text)
    discharge_note: Mapped[str | None] = mapped_column(Text)
    discharged_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    admitted_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    patient = relationship("Patient")
    bed = relationship("IPDBed", back_populates="admissions")
    attending_doctor = relationship("User", foreign_keys=[attending_doctor_user_id])
    admitted_by = relationship("User", foreign_keys=[admitted_by_user_id])
    discharged_by = relationship("User", foreign_keys=[discharged_by_user_id])
    movements = relationship("IPDAdmissionMovement", back_populates="admission", cascade="all, delete-orphan")


class IPDAdmissionMovement(Base, BaseModelMixin):
    __tablename__ = "ipd_admission_movements"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    from_ward_name: Mapped[str | None] = mapped_column(String(120))
    from_bed_number: Mapped[str | None] = mapped_column(String(60))
    to_ward_name: Mapped[str | None] = mapped_column(String(120))
    to_bed_number: Mapped[str | None] = mapped_column(String(60))
    note: Mapped[str | None] = mapped_column(Text)
    moved_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    admission = relationship("IPDAdmission", back_populates="movements")
    moved_by = relationship("User", foreign_keys=[moved_by_user_id])


class ERVisit(Base, BaseModelMixin):
    __tablename__ = "er_visits"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    visit_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    arrival_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="walk_in")
    arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(120))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20))
    triage_category: Mapped[str] = mapped_column(String(30), nullable=False, default="yellow")
    triage_level: Mapped[int] = mapped_column(nullable=False, default=3)
    vitals: Mapped[str | None] = mapped_column(Text)
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    initial_diagnosis: Mapped[str | None] = mapped_column(Text)
    assigned_doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    assigned_nurse_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    assigned_location: Mapped[str | None] = mapped_column(String(120))
    treatment_status: Mapped[str | None] = mapped_column(String(40), default="pending")
    treatment_notes: Mapped[str | None] = mapped_column(Text)
    disposition: Mapped[str | None] = mapped_column(String(255))
    referral_hospital: Mapped[str | None] = mapped_column(String(150))
    referral_doctor_name: Mapped[str | None] = mapped_column(String(150))
    disposition_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="waiting")
    admitted_to_ipd_admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    discharged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    branch = relationship("Branch")
    patient = relationship("Patient")
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_user_id])
    assigned_nurse = relationship("User", foreign_keys=[assigned_nurse_user_id])
    admitted_to_ipd_admission = relationship("IPDAdmission", foreign_keys=[admitted_to_ipd_admission_id])
    ambulance_records = relationship("ERAmbulanceRecord", back_populates="er_visit", cascade="all, delete-orphan")


class ERAmbulanceRecord(Base, BaseModelMixin):
    __tablename__ = "er_ambulance_records"

    er_visit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("er_visits.id"), nullable=False)
    ambulance_service: Mapped[str] = mapped_column(String(120), nullable=False)
    driver_name: Mapped[str | None] = mapped_column(String(120))
    pickup_location: Mapped[str | None] = mapped_column(String(255))
    drop_off_location: Mapped[str | None] = mapped_column(String(255))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    er_visit = relationship("ERVisit", back_populates="ambulance_records")


class Appointment(Base, BaseModelMixin):
    __tablename__ = "appointments"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    appointment_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    booked_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    booked_by_patient_account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_portal_accounts.id"), nullable=True)

    branch = relationship("Branch")
    patient = relationship("Patient")
    doctor = relationship("User", foreign_keys=[doctor_user_id])
    booked_by = relationship("User", foreign_keys=[booked_by_user_id])
    booked_by_patient_account = relationship("PatientPortalAccount", foreign_keys=[booked_by_patient_account_id])
    opd_visits = relationship("OPDVisit", back_populates="source_appointment")
