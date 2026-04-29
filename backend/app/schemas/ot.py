from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OTDashboardRead(BaseModel):
    today_surgeries: int
    upcoming_surgeries: int
    ongoing_surgeries: int
    completed_surgeries: int
    cancelled_surgeries: int
    emergency_surgeries: int
    available_rooms: int
    occupied_rooms: int
    pending_pre_op: int
    pending_anesthesia: int
    surgeon_schedule: dict[str, int]
    department_schedule: dict[str, int]
    room_utilization: list[dict]
    alerts: list[str]


class OTRoomCreate(BaseModel):
    room_number: str
    name: str
    room_type: str = "major"
    status: str = "available"
    floor: str | None = None
    equipment_summary: str | None = None
    hourly_charge: Decimal = Decimal("0")
    note: str | None = None


class OTRoomRead(OTRoomCreate):
    id: UUID
    model_config = {"from_attributes": True}


class OTBookingCreate(BaseModel):
    patient_id: UUID
    source_module: str | None = None
    source_reference_id: UUID | None = None
    procedure_name: str = Field(min_length=2)
    surgery_type: str = "elective"
    priority_level: str = "normal"
    preferred_start_at: datetime
    estimated_duration_minutes: int = 60
    department_name: str | None = None
    diagnosis: str | None = None
    note: str | None = None


class OTBookingRead(OTBookingCreate):
    id: UUID
    booking_number: str
    status: str
    patient_name: str | None = None
    patient_number: str | None = None
    model_config = {"from_attributes": True}


class SurgeryScheduleCreate(BaseModel):
    booking_id: UUID
    room_id: UUID
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    primary_surgeon_user_id: UUID | None = None
    assistant_surgeon_user_id: UUID | None = None
    anesthetist_user_id: UUID | None = None
    scrub_nurse_user_id: UUID | None = None
    circulating_nurse_user_id: UUID | None = None
    technician_user_id: UUID | None = None
    status: str = "scheduled"


class SurgeryScheduleRead(SurgeryScheduleCreate):
    id: UUID
    booking_number: str | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    procedure_name: str | None = None
    surgery_type: str | None = None
    priority_level: str | None = None
    department_name: str | None = None
    room_name: str | None = None
    room_number: str | None = None
    primary_surgeon_name: str | None = None
    anesthetist_name: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class TeamAssignmentCreate(BaseModel):
    schedule_id: UUID
    user_id: UUID | None = None
    role: str
    staff_name: str | None = None
    response_status: str = "assigned"
    note: str | None = None


class PreOpChecklistUpdate(BaseModel):
    consent_signed: bool = False
    anesthesia_cleared: bool = False
    lab_verified: bool = False
    radiology_verified: bool = False
    blood_arranged: bool = False
    npo_confirmed: bool = False
    site_marked: bool = False
    equipment_confirmed: bool = False
    implant_confirmed: bool = False
    allergy_info: str | None = None
    current_medication_review: str | None = None
    pre_op_diagnosis: str | None = None
    risk_assessment_notes: str | None = None
    ready_for_ot: bool = False


class AnesthesiaRecordUpdate(BaseModel):
    anesthesia_type: str = "general"
    pre_assessment: str | None = None
    notes: str | None = None
    anesthesia_start_at: datetime | None = None
    anesthesia_end_at: datetime | None = None
    medication_record: str | None = None
    fluid_record: str | None = None
    vitals_summary: str | None = None
    complications: str | None = None
    recovery_notes: str | None = None
    clearance_status: str = "pending"


class SurgeryNoteUpdate(BaseModel):
    procedure_performed: str | None = None
    operative_findings: str | None = None
    surgeon_notes: str | None = None
    nursing_notes: str | None = None
    instrument_count_confirmed: bool = False
    sponge_count_confirmed: bool = False
    implant_usage_details: str | None = None
    specimen_collection_details: str | None = None
    surgery_outcome: str = "successful"


class PostOpRecoveryUpdate(BaseModel):
    transfer_to: str = "recovery"
    recovery_admission_at: datetime | None = None
    vitals_summary: str | None = None
    pain_score: int | None = None
    consciousness_status: str | None = None
    post_op_instructions: str | None = None
    medication_instructions: str | None = None
    nursing_observations: str | None = None
    recovery_discharge_at: datetime | None = None
    handover_notes: str | None = None
    complication_summary: str | None = None


class OTConsumableUsageCreate(BaseModel):
    schedule_id: UUID
    inventory_item_id: UUID | None = None
    item_name: str
    batch_no: str | None = None
    quantity_used: Decimal = Decimal("0")
    quantity_returned: Decimal = Decimal("0")
    wastage_quantity: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    charged_amount: Decimal = Decimal("0")
    note: str | None = None


class OTEquipmentUsageCreate(BaseModel):
    schedule_id: UUID
    equipment_name: str
    usage_notes: str | None = None
    charge_amount: Decimal = Decimal("0")
    confirmed: bool = False


class OTBillingItemCreate(BaseModel):
    schedule_id: UUID
    charge_type: str
    description: str
    amount: Decimal
    payment_status: str = "pending"


class OTDocumentCreate(BaseModel):
    schedule_id: UUID
    document_type: str
    title: str
    file_url: str | None = None
    body: str | None = None
    status: str = "stored"


class OTCaseSheetRead(BaseModel):
    schedule: dict
    pre_op: dict | None = None
    anesthesia: dict | None = None
    surgery_note: dict | None = None
    recovery: dict | None = None
    consumables: list[dict]
    equipment: list[dict]
    billing: list[dict]
    documents: list[dict]


class OTStatusUpdate(BaseModel):
    status: str
    note: str | None = None
