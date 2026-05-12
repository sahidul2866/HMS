from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class BloodBankDashboardFilter(BaseModel):
    blood_group: str | None = None
    component_type: str | None = None
    expiry_status: str | None = None
    storage_location_id: UUID | None = None
    request_status: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class BloodBankDashboardRead(BaseModel):
    available_units_by_group: dict[str, int]
    available_components_by_group: dict[str, dict[str, int]]
    low_stock_groups: list[str]
    near_expiry_units: int
    expired_units: int
    pending_donor_screening: int
    pending_crossmatch_requests: int
    pending_issue_requests: int
    issued_units: int
    discarded_units: int
    emergency_requests: int
    unsafe_units_blocked: int


class BloodDonorCreate(BaseModel):
    donor_number: str | None = None
    name: str = Field(min_length=2, max_length=160)
    date_of_birth: date | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = None
    blood_group: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    last_donation_date: date | None = None
    eligibility_status: str = "unknown"
    medical_screening_status: str = "pending"
    remarks: str | None = None


class BloodDonorUpdate(BloodDonorCreate):
    pass


class BloodDonorRead(BloodDonorCreate):
    id: UUID
    donor_number: str
    donation_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DonorScreeningCreate(BaseModel):
    donor_id: UUID
    weight: Decimal | None = Field(default=None, ge=0)
    hemoglobin_level: Decimal | None = Field(default=None, ge=0)
    blood_pressure: str | None = None
    temperature: Decimal | None = None
    pulse: int | None = Field(default=None, ge=0)
    medical_history: dict[str, Any] | None = None
    recent_illness: str | None = None
    medication_history: str | None = None
    travel_history: str | None = None
    previous_donation_date: date | None = None
    eligibility_result: str
    deferral_reason: str | None = None
    next_eligible_date: date | None = None
    screened_at: datetime | None = None
    override_authorized: bool = False
    remarks: str | None = None


class DonorScreeningRead(DonorScreeningCreate):
    id: UUID
    screening_staff_id: UUID | None = None
    donor_name: str | None = None

    model_config = {"from_attributes": True}


class BloodCollectionCreate(BaseModel):
    donor_id: UUID
    screening_id: UUID | None = None
    unit_number: str | None = None
    blood_group: str
    collection_volume_ml: int | None = Field(default=None, ge=0)
    bag_type: str | None = None
    anticoagulant_type: str | None = None
    collected_at: datetime | None = None
    collection_location: str | None = None
    remarks: str | None = None


class BloodCollectionRead(BloodCollectionCreate):
    id: UUID
    collection_number: str
    unit_number: str
    donor_name: str | None = None

    model_config = {"from_attributes": True}


class BloodUnitRead(BaseModel):
    id: UUID
    unit_number: str
    blood_group: str
    rh_factor: str | None = None
    component_type: str
    collection_date: date | None = None
    expiry_date: date | None = None
    volume_ml: int | None = None
    storage_location_id: UUID | None = None
    storage_location_name: str | None = None
    status: str
    testing_status: str
    donor_id: UUID | None = None
    current_patient_id: UUID | None = None
    remarks: str | None = None

    model_config = {"from_attributes": True}


class BloodTestResultCreate(BaseModel):
    unit_id: UUID
    test_name: str
    test_code: str | None = None
    status: str = "pending"
    result: str | None = None
    result_value: str | None = None
    lab_order_id: UUID | None = None
    performed_at: datetime | None = None
    verified: bool = False
    remarks: str | None = None


class BloodTestResultRead(BloodTestResultCreate):
    id: UUID
    performed_by: UUID | None = None
    verified_by: UUID | None = None
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class ComponentPrepareCreate(BaseModel):
    source_unit_id: UUID
    component_type: str
    component_unit_number: str | None = None
    prepared_at: datetime | None = None
    expiry_date: date
    volume_ml: int | None = Field(default=None, ge=0)
    storage_location_id: UUID | None = None
    remarks: str | None = None


class StorageLocationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=160)
    location_type: str = "refrigerator"
    parent_location_id: UUID | None = None
    temperature_min: Decimal | None = None
    temperature_max: Decimal | None = None
    current_temperature: Decimal | None = None
    remarks: str | None = None


class StorageLocationRead(StorageLocationCreate):
    id: UUID

    model_config = {"from_attributes": True}


class MoveUnitCreate(BaseModel):
    storage_location_id: UUID
    remarks: str | None = None


class BloodRequestCreate(BaseModel):
    patient_id: UUID
    admission_id: UUID | None = None
    er_visit_id: UUID | None = None
    ot_booking_id: UUID | None = None
    requesting_doctor_id: UUID | None = None
    department_id: UUID | None = None
    department_name: str | None = None
    blood_group: str
    component_type: str
    quantity_units: int = Field(default=1, gt=0)
    urgency: str = "routine"
    indication: str | None = None
    required_at: datetime | None = None
    diagnosis: str | None = None
    status: str = "requested"
    payment_status: str | None = None
    override_reason: str | None = None
    remarks: str | None = None


class BloodRequestRead(BloodRequestCreate):
    id: UUID
    request_number: str
    patient_name: str | None = None

    model_config = {"from_attributes": True}


class CrossmatchCreate(BaseModel):
    request_id: UUID
    unit_id: UUID
    patient_blood_group: str
    result: str
    compatibility_status: str
    verified_by: UUID | None = None
    tested_at: datetime | None = None
    emergency_override: bool = False
    override_reason: str | None = None
    remarks: str | None = None


class CrossmatchRead(CrossmatchCreate):
    id: UUID
    unit_number: str | None = None
    unit_blood_group: str
    component_type: str
    tested_by: UUID | None = None

    model_config = {"from_attributes": True}


class BloodIssueCreate(BaseModel):
    request_id: UUID
    unit_id: UUID
    crossmatch_id: UUID | None = None
    received_by: str | None = None
    issued_at: datetime | None = None
    destination: str | None = None
    transport_condition: str | None = None
    create_billing: bool = False
    emergency_override: bool = False
    override_reason: str | None = None
    remarks: str | None = None


class BloodIssueRead(BloodIssueCreate):
    id: UUID
    issue_number: str
    patient_id: UUID
    unit_number: str | None = None
    blood_group: str | None = None
    component_type: str | None = None

    model_config = {"from_attributes": True}


class TransfusionCreate(BaseModel):
    issue_id: UUID
    status: str = "started"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    vitals: dict[str, Any] | None = None
    reaction_observed: bool = False
    reaction_details: str | None = None
    remarks: str | None = None


class TransfusionRead(TransfusionCreate):
    id: UUID
    unit_id: UUID
    patient_id: UUID

    model_config = {"from_attributes": True}


class BloodReturnCreate(BaseModel):
    issue_id: UUID
    returned_by: str | None = None
    returned_at: datetime | None = None
    condition_on_return: str | None = None
    minutes_outside_bank: int | None = Field(default=None, ge=0)
    reason: str | None = None
    decision: str
    remarks: str | None = None


class BloodReturnRead(BloodReturnCreate):
    id: UUID
    unit_id: UUID

    model_config = {"from_attributes": True}


class BloodDiscardCreate(BaseModel):
    unit_id: UUID
    reason: str
    details: str | None = None
    discarded_at: datetime | None = None
    approved_by: UUID | None = None


class BloodDiscardRead(BloodDiscardCreate):
    id: UUID

    model_config = {"from_attributes": True}


class BloodBankReportRead(BaseModel):
    report_type: str
    generated_at: datetime
    rows: list[dict[str, Any]]
    totals: dict[str, Any]

