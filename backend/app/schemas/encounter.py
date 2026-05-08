from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.patient import PatientRead


class VisitType(str, Enum):
    NEW = "new"
    FOLLOW_UP = "follow_up"


class OPDVisitCreate(BaseModel):
    patient_id: UUID
    visit_date: date
    slot_start_at: datetime | None = None
    department_name: str = Field(min_length=2, max_length=120)
    doctor_user_id: UUID | None = None
    consulting_doctor_name: str = Field(min_length=2, max_length=150)
    consultation_fee: Decimal = Field(default=0, ge=0)
    visit_type: VisitType = VisitType.NEW
    chief_complaint: str | None = None
    note: str | None = None


class OPDVisitConsultationUpdate(BaseModel):
    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    past_history: str | None = None
    vital_signs: str | None = None
    examination_note: str | None = None
    provisional_diagnosis: str | None = None
    final_diagnosis: str | None = None
    follow_up_date: date | None = None
    follow_up_note: str | None = None
    note: str | None = None


class OPDVisitUpdate(BaseModel):
    visit_date: date
    slot_start_at: datetime | None = None
    department_name: str = Field(min_length=2, max_length=120)
    doctor_user_id: UUID | None = None
    consulting_doctor_name: str = Field(min_length=2, max_length=150)
    chief_complaint: str | None = None
    consultation_fee: Decimal = Field(default=0, ge=0)
    note: str | None = None


class OPDVisitPaymentUpdate(BaseModel):
    amount: Decimal = Field(ge=0)
    discount: Decimal = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_discount(self) -> "OPDVisitPaymentUpdate":
        if self.discount > self.amount:
            raise ValueError("Discount cannot exceed amount")
        return self


class OPDVisitStatusUpdate(BaseModel):
    status: str = Field(pattern="^(waiting|in_consultation|prescribed|billed|completed|cancelled)$")


class OPDVisitOrderCreate(BaseModel):
    order_type: str = Field(pattern="^(prescription|investigation|procedure)$")
    service_area: str | None = Field(default=None, pattern="^(pharmacy|laboratory|radiology)$")
    item_name: str = Field(min_length=2, max_length=180)
    room_number: str | None = Field(default=None, max_length=60)
    instructions: str | None = None
    quantity: Decimal = Field(default=1, ge=0.01)

    @model_validator(mode="after")
    def validate_service_area(self) -> "OPDVisitOrderCreate":
        if self.order_type == "investigation" and not self.service_area:
            raise ValueError("Investigation orders require a service area")
        if self.order_type == "investigation" and self.service_area == "pharmacy":
            raise ValueError("Investigation orders require laboratory or radiology service area")
        if self.order_type == "prescription":
            self.service_area = "pharmacy"
        if self.order_type == "procedure":
            self.service_area = None
        return self


class OPDVisitOrderUpdate(BaseModel):
    service_area: str | None = Field(default=None, pattern="^(pharmacy|laboratory|radiology)$")
    item_name: str | None = Field(default=None, min_length=2, max_length=180)
    room_number: str | None = Field(default=None, max_length=60)
    instructions: str | None = None
    quantity: Decimal | None = Field(default=None, ge=0.01)
    status: str | None = Field(default=None, pattern="^(pending|scheduled|collected|in_progress|completed|verified|cancelled)$")
    result_text: str | None = None
    sample_note: str | None = None


class OPDVisitOrderRead(OPDVisitOrderCreate):
    id: UUID
    status: str
    sample_note: str | None = None
    sample_collected_at: datetime | None = None
    result_text: str | None = None
    completed_at: datetime | None = None
    verified_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OPDVisitRead(OPDVisitCreate):
    id: UUID
    visit_number: str
    status: str
    consulting_doctor_user_id: UUID | None = None
    converted_ipd_admission_id: UUID | None = None
    history_of_present_illness: str | None = None
    past_history: str | None = None
    vital_signs: str | None = None
    examination_note: str | None = None
    provisional_diagnosis: str | None = None
    final_diagnosis: str | None = None
    follow_up_date: date | None = None
    follow_up_note: str | None = None
    consultation_discount: Decimal = 0
    consultation_total: Decimal = 0
    consultation_payment_status: str = "unpaid"
    consultation_paid_at: datetime | None = None
    patient: PatientRead
    orders: list[OPDVisitOrderRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class OPDSummary(BaseModel):
    total_visits: int
    waiting_visits: int
    in_consultation_visits: int
    completed_visits: int


class ERVisitArrivalMode(str, Enum):
    WALK_IN = "walk_in"
    AMBULANCE = "ambulance"
    TRANSFER = "transfer"


class ERVisitStatus(str, Enum):
    WAITING = "waiting"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    IN_TREATMENT = "in_treatment"
    ADMITTED = "admitted"
    DISCHARGED = "discharged"
    REFERRED = "referred"
    CANCELLED = "cancelled"


class ERVisitTriageUpdate(BaseModel):
    triage_category: str = Field(pattern="^(red|orange|yellow|green|blue)$")
    triage_level: int = Field(ge=1, le=5)
    vitals: str | None = None
    note: str | None = None


class ERVisitAssignmentUpdate(BaseModel):
    assigned_doctor_user_id: UUID | None = None
    assigned_nurse_user_id: UUID | None = None
    assigned_location: str | None = Field(default=None, max_length=120)
    note: str | None = None


class ERVisitTreatmentUpdate(BaseModel):
    treatment_status: str = Field(pattern="^(pending|under_assessment|orders_pending|in_progress|observation|ready_for_disposition|completed|review_needed)$")
    treatment_notes: str | None = None
    disposition: str | None = Field(default=None, max_length=255)
    referral_hospital: str | None = Field(default=None, max_length=150)
    referral_doctor_name: str | None = Field(default=None, max_length=150)
    disposition_note: str | None = None


class ERVisitStatusUpdate(BaseModel):
    status: str = Field(pattern="^(registered|waiting|waiting_for_triage|triaged|waiting_for_doctor|under_assessment|orders_pending|assigned|in_treatment|observation|ready_for_disposition|admitted|transferred|discharged|left_without_being_seen|left_against_medical_advice|death_recorded|referred|cancelled)$")
    note: str | None = None


class ERVisitAmbulanceCreate(BaseModel):
    ambulance_service: str = Field(min_length=2, max_length=120)
    driver_name: str | None = Field(default=None, max_length=120)
    pickup_location: str | None = Field(default=None, max_length=255)
    drop_off_location: str | None = Field(default=None, max_length=255)
    received_at: datetime
    note: str | None = None


class ERVisitAmbulanceRead(ERVisitAmbulanceCreate):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ERVisitCreate(BaseModel):
    patient_id: UUID
    arrival_mode: ERVisitArrivalMode = ERVisitArrivalMode.WALK_IN
    arrival_time: datetime
    source_reference: str | None = Field(default=None, max_length=120)
    emergency_contact_name: str | None = Field(default=None, max_length=120)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    triage_category: str = Field(pattern="^(red|orange|yellow|green|blue)$", default="yellow")
    triage_level: int = Field(ge=1, le=5, default=3)
    chief_complaint: str | None = Field(default=None, max_length=500)
    initial_diagnosis: str | None = Field(default=None, max_length=500)
    preferred_doctor_user_id: UUID | None = None
    assigned_nurse_user_id: UUID | None = None
    assigned_location: str | None = Field(default=None, max_length=120)
    note: str | None = None


class ERVisitConvertToIPD(BaseModel):
    bed_id: UUID | None = None
    admitted_at: datetime
    admission_type: str = Field(min_length=2, max_length=30)
    ward_name: str = Field(min_length=2, max_length=120)
    bed_number: str = Field(min_length=1, max_length=60)
    doctor_user_id: UUID | None = None
    attending_doctor_name: str = Field(min_length=2, max_length=150)
    diagnosis: str | None = None
    daily_charge: Decimal = Field(default=0, ge=0)
    advance_amount: Decimal = Field(default=0, ge=0)
    expected_discharge_date: date | None = None


class ERVisitRead(ERVisitCreate):
    id: UUID
    visit_number: str
    status: str
    treatment_status: str | None = None
    assigned_doctor_user_id: UUID | None = None
    assigned_nurse_user_id: UUID | None = None
    admitted_to_ipd_admission_id: UUID | None = None
    discharged_at: datetime | None = None
    patient: PatientRead
    ambulance_records: list[ERVisitAmbulanceRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ERSummary(BaseModel):
    total_visits: int
    waiting_visits: int
    triaged_visits: int
    assigned_visits: int
    in_treatment_visits: int
    admitted_visits: int
    discharged_visits: int
    referred_visits: int


class IPDAdmissionCreate(BaseModel):
    patient_id: UUID
    bed_id: UUID | None = None
    admitted_at: datetime
    admission_type: str = Field(min_length=2, max_length=30)
    ward_name: str = Field(min_length=2, max_length=120)
    bed_number: str = Field(min_length=1, max_length=60)
    doctor_user_id: UUID | None = None
    attending_doctor_name: str = Field(min_length=2, max_length=150)
    diagnosis: str | None = None
    daily_charge: Decimal = Field(default=0, ge=0)
    advance_amount: Decimal = Field(default=0, ge=0)
    expected_discharge_date: date | None = None


class IPDDischarge(BaseModel):
    discharge_condition: str | None = Field(default=None, max_length=120)
    discharge_diagnosis: str | None = None
    discharge_summary: str | None = None
    discharge_note: str | None = None


class IPDTransfer(BaseModel):
    bed_id: UUID | None = None
    ward_name: str = Field(min_length=2, max_length=120)
    bed_number: str = Field(min_length=1, max_length=60)
    note: str | None = None


class IPDAdmissionMovementRead(BaseModel):
    id: UUID
    movement_type: str
    moved_at: datetime
    from_ward_name: str | None = None
    from_bed_number: str | None = None
    to_ward_name: str | None = None
    to_bed_number: str | None = None
    note: str | None = None
    moved_by_user_id: UUID

    model_config = {"from_attributes": True}


class IPDAdmissionRead(IPDAdmissionCreate):
    id: UUID
    admission_number: str
    attending_doctor_user_id: UUID | None = None
    status: str
    discharged_at: datetime | None = None
    discharge_condition: str | None = None
    discharge_diagnosis: str | None = None
    discharge_summary: str | None = None
    discharge_note: str | None = None
    patient: PatientRead
    movements: list[IPDAdmissionMovementRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class IPDSummary(BaseModel):
    total_admissions: int
    active_admissions: int
    discharged_admissions: int
    occupied_beds: int


class IPDBedCreate(BaseModel):
    ward_name: str = Field(min_length=2, max_length=120)
    bed_number: str = Field(min_length=1, max_length=60)
    bed_type: str = Field(min_length=2, max_length=40)
    daily_rate: Decimal = Field(default=0, ge=0)
    note: str | None = None


class IPDBedRead(IPDBedCreate):
    id: UUID
    status: str

    model_config = {"from_attributes": True}


class OPDConvertToIPD(BaseModel):
    bed_id: UUID | None = None
    admitted_at: datetime
    admission_type: str = Field(min_length=2, max_length=30)
    ward_name: str = Field(min_length=2, max_length=120)
    bed_number: str = Field(min_length=1, max_length=60)
    doctor_user_id: UUID | None = None
    attending_doctor_name: str = Field(min_length=2, max_length=150)
    diagnosis: str | None = None
    daily_charge: Decimal = Field(default=0, ge=0)
    advance_amount: Decimal = Field(default=0, ge=0)
    expected_discharge_date: date | None = None


class ClinicalInvestigationWorkItemRead(BaseModel):
    order_id: UUID
    visit_id: UUID
    visit_number: str
    visit_date: date
    patient_id: UUID
    patient_number: str
    patient_name: str
    consulting_doctor_name: str
    service_area: str
    item_name: str
    room_number: str | None = None
    quantity: Decimal
    instructions: str | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None
    status: str
    sample_note: str | None = None
    sample_collected_at: datetime | None = None
    result_text: str | None = None
    completed_at: datetime | None = None
    verified_at: datetime | None = None
    has_pacs_link: bool = False
    pacs_study_uid: str | None = None
    lab_order_id: UUID | None = None
    radiology_order_id: UUID | None = None


class ClinicalInvestigationResultUpdate(BaseModel):
    status: str = Field(pattern="^(collected|in_progress|completed|verified|cancelled)$")
    sample_note: str | None = None
    result_text: str | None = None
