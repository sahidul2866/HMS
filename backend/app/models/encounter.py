from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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
    slot_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    queue_number: Mapped[str | None] = mapped_column(String(40), index=True)
    queue_status: Mapped[str | None] = mapped_column(String(40), index=True)
    queue_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    lab_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"))
    radiology_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_orders.id"))

    visit = relationship("OPDVisit", back_populates="orders")
    sample_collected_by = relationship("User", foreign_keys=[sample_collected_by_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    lab_order = relationship("LabOrder", foreign_keys=[lab_order_id])
    radiology_order = relationship("RadiologyOrder", foreign_keys=[radiology_order_id])


class IPDAdmission(Base, BaseModelMixin):
    __tablename__ = "ipd_admissions"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    bed_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_beds.id"))
    attending_doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    assigned_nurse_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    admission_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    admission_type: Mapped[str] = mapped_column(String(30), nullable=False, default="general")
    admission_source: Mapped[str | None] = mapped_column(String(40))
    department_name: Mapped[str | None] = mapped_column(String(120))
    payment_type: Mapped[str | None] = mapped_column(String(60))
    insurance_info: Mapped[str | None] = mapped_column(Text)
    patient_condition: Mapped[str | None] = mapped_column(Text)
    ward_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bed_number: Mapped[str] = mapped_column(String(60), nullable=False)
    attending_doctor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    daily_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="admitted")
    billing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="unbilled")
    discharge_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_planned")
    pharmacy_clearance_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    lab_clearance_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    radiology_clearance_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
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
    assigned_nurse = relationship("User", foreign_keys=[assigned_nurse_user_id])
    admitted_by = relationship("User", foreign_keys=[admitted_by_user_id])
    discharged_by = relationship("User", foreign_keys=[discharged_by_user_id])
    movements = relationship("IPDAdmissionMovement", back_populates="admission", cascade="all, delete-orphan")
    staff_assignments = relationship("IPDStaffAssignment", back_populates="admission", cascade="all, delete-orphan")
    clinical_notes = relationship("IPDClinicalNote", back_populates="admission", cascade="all, delete-orphan")
    nursing_notes = relationship("IPDNursingNote", back_populates="admission", cascade="all, delete-orphan")
    orders = relationship("IPDOrder", back_populates="admission", cascade="all, delete-orphan")
    medication_administrations = relationship("IPDMedicationAdministration", back_populates="admission", cascade="all, delete-orphan")
    handovers = relationship("IPDHandover", back_populates="admission", cascade="all, delete-orphan")
    nursing_tasks = relationship("IPDNursingTask", back_populates="admission", cascade="all, delete-orphan")
    timeline_events = relationship("IPDTimelineEvent", back_populates="admission", cascade="all, delete-orphan")


class IPDAdmissionMovement(Base, BaseModelMixin):
    __tablename__ = "ipd_admission_movements"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    from_ward_name: Mapped[str | None] = mapped_column(String(120))
    from_bed_number: Mapped[str | None] = mapped_column(String(60))
    to_ward_name: Mapped[str | None] = mapped_column(String(120))
    to_bed_number: Mapped[str | None] = mapped_column(String(60))
    transfer_reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)
    moved_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    admission = relationship("IPDAdmission", back_populates="movements")
    moved_by = relationship("User", foreign_keys=[moved_by_user_id])
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])


class IPDStaffAssignment(Base, BaseModelMixin):
    __tablename__ = "ipd_staff_assignments"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    staff_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    staff_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role_type: Mapped[str] = mapped_column(String(40), nullable=False)
    assignment_type: Mapped[str] = mapped_column(String(60), nullable=False, default="primary")
    shift_name: Mapped[str | None] = mapped_column(String(80))
    ward_name: Mapped[str | None] = mapped_column(String(120))
    bed_number: Mapped[str | None] = mapped_column(String(60))
    department_name: Mapped[str | None] = mapped_column(String(120))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    override_reason: Mapped[str | None] = mapped_column(Text)
    schedule_status: Mapped[str | None] = mapped_column(String(60))
    assigned_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    changed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    admission = relationship("IPDAdmission", back_populates="staff_assignments")
    staff_user = relationship("User", foreign_keys=[staff_user_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])


class IPDClinicalNote(Base, BaseModelMixin):
    __tablename__ = "ipd_clinical_notes"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(60), nullable=False, default="progress_note")
    title: Mapped[str | None] = mapped_column(String(160))
    note: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    template_key: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    authored_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    authored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    admission = relationship("IPDAdmission", back_populates="clinical_notes")
    authored_by = relationship("User", foreign_keys=[authored_by_user_id])


class IPDNursingNote(Base, BaseModelMixin):
    __tablename__ = "ipd_nursing_notes"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(60), nullable=False, default="nursing_note")
    note: Mapped[str | None] = mapped_column(Text)
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    pulse: Mapped[int | None] = mapped_column(Integer)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer)
    systolic_bp: Mapped[int | None] = mapped_column(Integer)
    diastolic_bp: Mapped[int | None] = mapped_column(Integer)
    spo2: Mapped[int | None] = mapped_column(Integer)
    pain_score: Mapped[int | None] = mapped_column(Integer)
    intake_ml: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    output_ml: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    glucose: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    fall_risk: Mapped[str | None] = mapped_column(String(40))
    abnormal_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    admission = relationship("IPDAdmission", back_populates="nursing_notes")
    recorded_by = relationship("User", foreign_keys=[recorded_by_user_id])


class IPDOrder(Base, BaseModelMixin):
    __tablename__ = "ipd_orders"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    order_type: Mapped[str] = mapped_column(String(40), nullable=False)
    service_area: Mapped[str | None] = mapped_column(String(40))
    item_name: Mapped[str] = mapped_column(String(180), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="routine")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ordered")
    billing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="unbilled")
    order_set_code: Mapped[str | None] = mapped_column(String(120))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    frequency: Mapped[str | None] = mapped_column(String(80))
    duration: Mapped[str | None] = mapped_column(String(80))
    dose: Mapped[str | None] = mapped_column(String(80))
    route: Mapped[str | None] = mapped_column(String(80))
    lab_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"))
    radiology_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_orders.id"))
    discontinued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discontinued_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    ordered_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    admission = relationship("IPDAdmission", back_populates="orders")
    ordered_by = relationship("User", foreign_keys=[ordered_by_user_id])
    lab_order = relationship("LabOrder", foreign_keys=[lab_order_id])
    radiology_order = relationship("RadiologyOrder", foreign_keys=[radiology_order_id])
    discontinued_by = relationship("User", foreign_keys=[discontinued_by_user_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_user_id])
    nursing_tasks = relationship("IPDNursingTask", back_populates="order", cascade="all, delete-orphan")


class IPDMedicationAdministration(Base, BaseModelMixin):
    __tablename__ = "ipd_medication_administrations"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_orders.id"))
    medicine_name: Mapped[str] = mapped_column(String(180), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(80))
    route: Mapped[str | None] = mapped_column(String(80))
    frequency: Mapped[str | None] = mapped_column(String(80))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    administered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="due")
    reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    administered_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    admission = relationship("IPDAdmission", back_populates="medication_administrations")
    order = relationship("IPDOrder")
    administered_by = relationship("User", foreign_keys=[administered_by_user_id])


class IPDNursingTask(Base, BaseModelMixin):
    __tablename__ = "ipd_nursing_tasks"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_orders.id"))
    assigned_nurse_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    ward_name: Mapped[str | None] = mapped_column(String(120))
    bed_number: Mapped[str | None] = mapped_column(String(60))
    shift_name: Mapped[str | None] = mapped_column(String(80))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    completion_note: Mapped[str | None] = mapped_column(Text)

    admission = relationship("IPDAdmission", back_populates="nursing_tasks")
    order = relationship("IPDOrder", back_populates="nursing_tasks")
    assigned_nurse = relationship("User", foreign_keys=[assigned_nurse_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])


class IPDHandover(Base, BaseModelMixin):
    __tablename__ = "ipd_handovers"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    handover_type: Mapped[str] = mapped_column(String(40), nullable=False, default="nursing")
    shift_name: Mapped[str | None] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    pending_items: Mapped[str | None] = mapped_column(Text)
    precautions: Mapped[str | None] = mapped_column(Text)
    sender_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    handed_over_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_ack")
    patient_condition: Mapped[str | None] = mapped_column(Text)
    active_diagnosis: Mapped[str | None] = mapped_column(Text)
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    pending_orders: Mapped[str | None] = mapped_column(Text)
    medication_due: Mapped[str | None] = mapped_column(Text)
    abnormal_vitals: Mapped[str | None] = mapped_column(Text)
    critical_alerts: Mapped[str | None] = mapped_column(Text)
    discharge_tasks: Mapped[str | None] = mapped_column(Text)
    special_instructions: Mapped[str | None] = mapped_column(Text)

    admission = relationship("IPDAdmission", back_populates="handovers")
    sender = relationship("User", foreign_keys=[sender_user_id])
    receiver = relationship("User", foreign_keys=[receiver_user_id])


class IPDTimelineEvent(Base, BaseModelMixin):
    __tablename__ = "ipd_timeline_events"

    admission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(80))
    source_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    admission = relationship("IPDAdmission", back_populates="timeline_events")
    actor = relationship("User", foreign_keys=[actor_user_id])


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
    slot_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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


class DoctorOPDSchedule(Base, BaseModelMixin):
    __tablename__ = "doctor_opd_schedules"
    __table_args__ = (UniqueConstraint("doctor_user_id", "weekday", name="uq_doctor_opd_schedule_day"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    doctor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # Monday=0 ... Sunday=6
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    branch = relationship("Branch")
    doctor = relationship("User", foreign_keys=[doctor_user_id])


class DoctorSlotBooking(Base, BaseModelMixin):
    __tablename__ = "doctor_slot_bookings"
    __table_args__ = (UniqueConstraint("doctor_user_id", "slot_start_at", name="uq_doctor_slot_start"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    doctor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    slot_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="appointment")
    appointment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("appointments.id"))
    opd_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked")

    branch = relationship("Branch")
    doctor = relationship("User", foreign_keys=[doctor_user_id])
    patient = relationship("Patient")
    appointment = relationship("Appointment")
    opd_visit = relationship("OPDVisit")
