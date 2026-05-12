from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class BloodBankSetting(Base, BaseModelMixin):
    __tablename__ = "blood_bank_settings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    setting_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (UniqueConstraint("branch_id", "setting_key", name="uq_blood_bank_settings_branch_key"),)


class BloodStorageLocation(Base, BaseModelMixin):
    __tablename__ = "blood_storage_locations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location_type: Mapped[str] = mapped_column(String(60), nullable=False, default="refrigerator")
    parent_location_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_storage_locations.id"))
    temperature_min: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    temperature_max: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    current_temperature: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    remarks: Mapped[str | None] = mapped_column(Text)

    parent = relationship("BloodStorageLocation", remote_side="BloodStorageLocation.id")
    units = relationship("BloodUnit", back_populates="storage_location")

    __table_args__ = (UniqueConstraint("branch_id", "code", name="uq_blood_storage_locations_branch_code"),)


class BloodDonor(Base, BaseModelMixin):
    __tablename__ = "blood_donors"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    donor_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(30))
    blood_group: Mapped[str | None] = mapped_column(String(10), index=True)
    phone: Mapped[str | None] = mapped_column(String(30), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    last_donation_date: Mapped[date | None] = mapped_column(Date)
    eligibility_status: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False, index=True)
    medical_screening_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    remarks: Mapped[str | None] = mapped_column(Text)

    screenings = relationship("BloodDonorScreening", back_populates="donor")
    collections = relationship("BloodCollection", back_populates="donor")


class BloodDonorScreening(Base, BaseModelMixin):
    __tablename__ = "blood_donor_screenings"

    donor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_donors.id"), nullable=False, index=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    hemoglobin_level: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    blood_pressure: Mapped[str | None] = mapped_column(String(40))
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    pulse: Mapped[int | None] = mapped_column(Integer)
    medical_history: Mapped[dict | None] = mapped_column(JSON)
    recent_illness: Mapped[str | None] = mapped_column(Text)
    medication_history: Mapped[str | None] = mapped_column(Text)
    travel_history: Mapped[str | None] = mapped_column(Text)
    previous_donation_date: Mapped[date | None] = mapped_column(Date)
    eligibility_result: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    deferral_reason: Mapped[str | None] = mapped_column(Text)
    next_eligible_date: Mapped[date | None] = mapped_column(Date)
    screening_staff_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    screened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    override_authorized_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)

    donor = relationship("BloodDonor", back_populates="screenings")


class BloodCollection(Base, BaseModelMixin):
    __tablename__ = "blood_collections"

    donor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_donors.id"), nullable=False, index=True)
    screening_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_donor_screenings.id"))
    collection_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    unit_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    blood_group: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    collection_volume_ml: Mapped[int | None] = mapped_column(Integer)
    bag_type: Mapped[str | None] = mapped_column(String(80))
    anticoagulant_type: Mapped[str | None] = mapped_column(String(80))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collection_staff_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    collection_location: Mapped[str | None] = mapped_column(String(160))
    remarks: Mapped[str | None] = mapped_column(Text)

    donor = relationship("BloodDonor", back_populates="collections")
    units = relationship("BloodUnit", back_populates="collection")


class BloodUnit(Base, BaseModelMixin):
    __tablename__ = "blood_units"

    collection_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_collections.id"), index=True)
    donor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_donors.id"), index=True)
    source_unit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"))
    unit_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    blood_group: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rh_factor: Mapped[str | None] = mapped_column(String(10), index=True)
    component_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    collection_date: Mapped[date | None] = mapped_column(Date)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    volume_ml: Mapped[int | None] = mapped_column(Integer)
    batch_number: Mapped[str | None] = mapped_column(String(80))
    storage_location_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_storage_locations.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="testing_pending", nullable=False, index=True)
    testing_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    current_request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_requests.id"))
    current_patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    prepared_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)

    collection = relationship("BloodCollection", back_populates="units")
    storage_location = relationship("BloodStorageLocation", back_populates="units")
    source_unit = relationship("BloodUnit", remote_side="BloodUnit.id")


class BloodTestResult(Base, BaseModelMixin):
    __tablename__ = "blood_test_results"

    unit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"), nullable=False, index=True)
    test_name: Mapped[str] = mapped_column(String(120), nullable=False)
    test_code: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    result: Mapped[str | None] = mapped_column(String(80))
    result_value: Mapped[str | None] = mapped_column(String(160))
    lab_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"))
    performed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    verified_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)

    unit = relationship("BloodUnit")

    __table_args__ = (UniqueConstraint("unit_id", "test_name", name="uq_blood_test_results_unit_test"),)


class BloodRequest(Base, BaseModelMixin):
    __tablename__ = "blood_requests"

    request_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    er_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("er_visits.id"))
    ot_booking_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ot_bookings.id"))
    requesting_doctor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    department_name: Mapped[str | None] = mapped_column(String(120))
    blood_group: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    component_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    quantity_units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    urgency: Mapped[str] = mapped_column(String(40), default="routine", nullable=False, index=True)
    indication: Mapped[str | None] = mapped_column(Text)
    required_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    diagnosis: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="requested", nullable=False, index=True)
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    payment_status: Mapped[str | None] = mapped_column(String(40))
    emergency_override_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    override_reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)

    patient = relationship("Patient")


class BloodCrossmatch(Base, BaseModelMixin):
    __tablename__ = "blood_crossmatches"

    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_requests.id"), nullable=False, index=True)
    unit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"), nullable=False, index=True)
    patient_blood_group: Mapped[str] = mapped_column(String(10), nullable=False)
    unit_blood_group: Mapped[str] = mapped_column(String(10), nullable=False)
    component_type: Mapped[str] = mapped_column(String(80), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    compatibility_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tested_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    verified_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    emergency_override_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    override_reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)

    request = relationship("BloodRequest")
    unit = relationship("BloodUnit")

    __table_args__ = (UniqueConstraint("request_id", "unit_id", name="uq_blood_crossmatches_request_unit"),)


class BloodIssue(Base, BaseModelMixin):
    __tablename__ = "blood_issues"

    issue_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_requests.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    unit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"), nullable=False, index=True)
    crossmatch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_crossmatches.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    issued_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    received_by: Mapped[str | None] = mapped_column(String(160))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(160))
    transport_condition: Mapped[str | None] = mapped_column(String(160))
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    remarks: Mapped[str | None] = mapped_column(Text)

    request = relationship("BloodRequest")
    unit = relationship("BloodUnit")

    __table_args__ = (UniqueConstraint("unit_id", name="uq_blood_issues_unit_id"),)


class BloodTransfusion(Base, BaseModelMixin):
    __tablename__ = "blood_transfusions"

    issue_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_issues.id"), nullable=False, index=True)
    unit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="started", nullable=False, index=True)
    started_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vitals: Mapped[dict | None] = mapped_column(JSON)
    reaction_observed: Mapped[bool] = mapped_column(default=False, nullable=False)
    reaction_details: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)

    issue = relationship("BloodIssue")
    unit = relationship("BloodUnit")


class BloodReturn(Base, BaseModelMixin):
    __tablename__ = "blood_returns"

    issue_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_issues.id"), nullable=False, index=True)
    unit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"), nullable=False, index=True)
    returned_by: Mapped[str | None] = mapped_column(String(160))
    returned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    condition_on_return: Mapped[str | None] = mapped_column(String(160))
    minutes_outside_bank: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    checked_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)

    issue = relationship("BloodIssue")
    unit = relationship("BloodUnit")


class BloodDiscard(Base, BaseModelMixin):
    __tablename__ = "blood_discards"

    unit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_units.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    discarded_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    discarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    unit = relationship("BloodUnit")

