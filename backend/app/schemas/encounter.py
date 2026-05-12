from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
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
    queue_number: str | None = None
    queue_status: str | None = None
    queue_called_at: datetime | None = None
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
    admission_source: str | None = Field(default=None, max_length=40)
    department_name: str | None = Field(default=None, max_length=120)
    payment_type: str | None = Field(default=None, max_length=60)
    insurance_info: str | None = None
    patient_condition: str | None = None
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
    allow_override: bool = False
    override_reason: str | None = None


class IPDTransfer(BaseModel):
    bed_id: UUID | None = None
    ward_name: str = Field(min_length=2, max_length=120)
    bed_number: str = Field(min_length=1, max_length=60)
    transfer_reason: str | None = None
    transfer_time: datetime | None = None
    approved_by_user_id: UUID | None = None
    remarks: str | None = None
    note: str | None = None


class IPDAdmissionMovementRead(BaseModel):
    id: UUID
    movement_type: str
    moved_at: datetime
    from_ward_name: str | None = None
    from_bed_number: str | None = None
    to_ward_name: str | None = None
    to_bed_number: str | None = None
    transfer_reason: str | None = None
    remarks: str | None = None
    requested_by_user_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    note: str | None = None
    moved_by_user_id: UUID

    model_config = {"from_attributes": True}


class IPDAdmissionRead(IPDAdmissionCreate):
    id: UUID
    admission_number: str
    attending_doctor_user_id: UUID | None = None
    assigned_nurse_user_id: UUID | None = None
    status: str
    billing_status: str = "unbilled"
    discharge_status: str = "not_planned"
    pharmacy_clearance_status: str = "pending"
    lab_clearance_status: str = "pending"
    radiology_clearance_status: str = "pending"
    pending_orders: int = 0
    pending_handovers: int = 0
    due_medications: int = 0
    current_shift: str | None = None
    handover_status: str = "clear"
    active_doctors: list["IPDStaffAssignmentRead"] = []
    active_nurses: list["IPDStaffAssignmentRead"] = []
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
    pending_orders: int = 0
    pending_handovers: int = 0
    discharge_planned: int = 0


class IPDBedBoardRow(BaseModel):
    bed_id: UUID
    ward_name: str
    room_type: str | None = None
    bed_number: str
    bed_type: str
    daily_rate: Decimal
    bed_status: str
    board_status: str
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    admission_id: UUID | None = None
    admission_number: str | None = None
    department_name: str | None = None
    doctor_name: str | None = None
    nurse_name: str | None = None
    admitted_at: datetime | None = None
    discharge_status: str | None = None
    billing_status: str | None = None
    occupancy_hours: Decimal = Decimal("0")


class IPDDischargeReadiness(BaseModel):
    admission_id: UUID
    admission_number: str
    status: str
    ready: bool
    checks: list[dict[str, Any]]
    blockers: list[str]
    discharge_summary_ready: bool
    final_bill_url: str | None = None


class IPDReportSummary(BaseModel):
    bed_occupancy: dict[str, Any]
    ward_census: list[dict[str, Any]]
    transfer_history: list[IPDAdmissionMovementRead]
    average_length_of_stay_days: Decimal
    discharge_status: dict[str, int]
    pending_discharge: list[IPDAdmissionRead]
    department_flow: list[dict[str, Any]]


class IPDSettings(BaseModel):
    ward_types: list[str] = Field(default_factory=list)
    room_types: list[str] = Field(default_factory=list)
    bed_types: list[str] = Field(default_factory=list)
    bed_statuses: list[str] = Field(default_factory=list)
    cleaning_statuses: list[str] = Field(default_factory=list)
    critical_care_categories: list[str] = Field(default_factory=list)
    default_bed_charges: dict[str, Decimal] = Field(default_factory=dict)
    admission_sources: list[str] = Field(default_factory=list)
    admission_types: list[str] = Field(default_factory=list)
    required_admission_fields: list[str] = Field(default_factory=list)
    admission_number_format: str = "IPD-{YYYY}{MM}{DD}-{SEQ4}"
    department_admission_rules: dict[str, Any] = Field(default_factory=dict)
    payment_type_rules: dict[str, Any] = Field(default_factory=dict)
    insurance_corporate_rules: dict[str, Any] = Field(default_factory=dict)
    doctor_assignment_types: list[str] = Field(default_factory=list)
    nurse_assignment_types: list[str] = Field(default_factory=list)
    max_patient_load_doctor: int = Field(default=20, ge=1)
    max_patient_load_nurse: int = Field(default=8, ge=1)
    department_staff_rules: dict[str, Any] = Field(default_factory=dict)
    shift_assignment_rules: dict[str, Any] = Field(default_factory=dict)
    on_call_assignment_rules: dict[str, Any] = Field(default_factory=dict)
    handover_templates: list[dict[str, Any]] = Field(default_factory=list)
    required_handover_fields: list[str] = Field(default_factory=list)
    shift_handover_timings: dict[str, str] = Field(default_factory=dict)
    require_handover_acknowledgment: bool = True
    handover_escalation_minutes: int = Field(default=30, ge=0)
    doctor_note_templates: list[dict[str, Any]] = Field(default_factory=list)
    nursing_note_templates: list[dict[str, Any]] = Field(default_factory=list)
    vitals_config: dict[str, Any] = Field(default_factory=dict)
    intake_output_settings: dict[str, Any] = Field(default_factory=dict)
    care_plan_templates: list[dict[str, Any]] = Field(default_factory=list)
    procedure_note_templates: list[dict[str, Any]] = Field(default_factory=list)
    discharge_approval_levels: list[str] = Field(default_factory=list)
    required_discharge_summary_fields: list[str] = Field(default_factory=list)
    clearance_requirements: dict[str, bool] = Field(default_factory=dict)
    billing_clearance_rules: dict[str, Any] = Field(default_factory=dict)
    pharmacy_clearance_rules: dict[str, Any] = Field(default_factory=dict)
    lab_radiology_pending_order_rules: dict[str, Any] = Field(default_factory=dict)
    follow_up_requirements: dict[str, Any] = Field(default_factory=dict)
    role_permission_notes: dict[str, list[str]] = Field(default_factory=dict)


class IPDSettingsRead(IPDSettings):
    id: UUID | None = None
    updated_at: datetime | None = None


class IPDSettingsUpdate(IPDSettings):
    pass


class IPDStaffAssignmentCreate(BaseModel):
    staff_user_id: UUID
    role_type: str = Field(pattern="^(doctor|nurse)$")
    assignment_type: str = Field(default="primary", max_length=60)
    shift_name: str | None = Field(default=None, max_length=80)
    reason: str | None = None
    allow_override: bool = False
    override_reason: str | None = None


class IPDStaffAssignmentRead(IPDStaffAssignmentCreate):
    id: UUID
    staff_name: str
    ward_name: str | None = None
    bed_number: str | None = None
    department_name: str | None = None
    assigned_at: datetime
    ended_at: datetime | None = None
    changed_at: datetime | None = None
    assigned_by_user_id: UUID
    changed_by_user_id: UUID | None = None
    schedule_status: str | None = None

    model_config = {"from_attributes": True}


class IPDStaffAvailabilityRead(BaseModel):
    staff_user_id: UUID
    staff_name: str
    role_type: str
    employee_id: UUID | None = None
    employee_status: str | None = None
    department_name: str | None = None
    current_shift: str | None = None
    duty_area: str | None = None
    roster_status: str | None = None
    is_on_duty: bool
    is_on_leave: bool
    active_ipd_assignments: int
    max_patient_load: int
    is_overloaded: bool
    can_assign: bool
    warnings: list[str] = []


class IPDShiftCoverageRead(BaseModel):
    shift_name: str
    ward_name: str | None = None
    doctors_on_duty: int = 0
    nurses_on_duty: int = 0
    doctor_gap: bool = False
    nurse_gap: bool = False
    warnings: list[str] = []


class IPDClinicalNoteCreate(BaseModel):
    note_type: str = Field(default="progress_note", max_length=60)
    title: str | None = Field(default=None, max_length=160)
    note: str = Field(min_length=1)
    diagnosis: str | None = None
    treatment_plan: str | None = None
    template_key: str | None = Field(default=None, max_length=120)


class IPDClinicalNoteRead(IPDClinicalNoteCreate):
    id: UUID
    version: int
    authored_by_user_id: UUID
    authored_at: datetime

    model_config = {"from_attributes": True}


class IPDNursingNoteCreate(BaseModel):
    note_type: str = Field(default="nursing_note", max_length=60)
    note: str | None = None
    temperature: Decimal | None = None
    pulse: int | None = None
    respiratory_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    spo2: int | None = None
    pain_score: int | None = None
    intake_ml: Decimal | None = None
    output_ml: Decimal | None = None
    glucose: Decimal | None = None
    fall_risk: str | None = Field(default=None, max_length=40)


class IPDNursingNoteRead(IPDNursingNoteCreate):
    id: UUID
    abnormal_alert: bool
    recorded_by_user_id: UUID
    recorded_at: datetime

    model_config = {"from_attributes": True}


class IPDOrderCreate(BaseModel):
    order_type: str = Field(pattern="^(medicine|lab|radiology|procedure|nursing|diet|monitoring)$")
    service_area: str | None = Field(default=None, max_length=40)
    item_name: str = Field(min_length=1, max_length=180)
    instructions: str | None = None
    quantity: Decimal = Field(default=1, gt=0)
    priority: str = Field(default="routine", max_length=40)
    order_set_code: str | None = Field(default=None, max_length=120)
    scheduled_at: datetime | None = None
    frequency: str | None = Field(default=None, max_length=80)
    duration: str | None = Field(default=None, max_length=80)
    dose: str | None = Field(default=None, max_length=80)
    route: str | None = Field(default=None, max_length=80)


class IPDOrderRead(IPDOrderCreate):
    id: UUID
    status: str
    billing_status: str
    lab_order_id: UUID | None = None
    radiology_order_id: UUID | None = None
    discontinued_at: datetime | None = None
    cancelled_at: datetime | None = None
    ordered_by_user_id: UUID
    ordered_at: datetime

    model_config = {"from_attributes": True}


class IPDOrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|active|completed|cancelled|discontinued)$")
    reason: str | None = None


class IPDOrderGroupRead(BaseModel):
    order_type: str
    status: str
    orders: list[IPDOrderRead]


class IPDMedicationAdministrationCreate(BaseModel):
    order_id: UUID | None = None
    medicine_name: str = Field(min_length=1, max_length=180)
    dose: str | None = Field(default=None, max_length=80)
    route: str | None = Field(default=None, max_length=80)
    frequency: str | None = Field(default=None, max_length=80)
    scheduled_at: datetime | None = None
    administered_at: datetime | None = None
    status: str = Field(default="administered", pattern="^(due|administered|skipped|held|delayed|refused)$")
    reason: str | None = None
    remarks: str | None = None
    allow_duplicate: bool = False


class IPDMedicationAdministrationRead(IPDMedicationAdministrationCreate):
    id: UUID
    administered_by_user_id: UUID | None = None

    model_config = {"from_attributes": True}


class IPDNursingTaskCreate(BaseModel):
    order_id: UUID | None = None
    assigned_nurse_user_id: UUID | None = None
    task_type: str = Field(max_length=60)
    title: str = Field(min_length=1, max_length=180)
    instructions: str | None = None
    shift_name: str | None = Field(default=None, max_length=80)
    due_at: datetime | None = None


class IPDNursingTaskUpdate(BaseModel):
    status: str = Field(pattern="^(pending|in_progress|completed|cancelled)$")
    completion_note: str | None = None


class IPDNursingTaskRead(IPDNursingTaskCreate):
    id: UUID
    admission_id: UUID
    ward_name: str | None = None
    bed_number: str | None = None
    status: str
    completed_at: datetime | None = None
    completed_by_user_id: UUID | None = None
    completion_note: str | None = None

    model_config = {"from_attributes": True}


class IPDVitalsTrendRead(BaseModel):
    recorded_at: datetime
    temperature: Decimal | None = None
    pulse: int | None = None
    respiratory_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    spo2: int | None = None
    pain_score: int | None = None
    glucose: Decimal | None = None
    abnormal_alert: bool


class IPDHandoverCreate(BaseModel):
    handover_type: str = Field(default="nursing", max_length=40)
    shift_name: str | None = Field(default=None, max_length=80)
    receiver_user_id: UUID | None = None
    summary: str = Field(min_length=1)
    pending_items: str | None = None
    precautions: str | None = None
    patient_condition: str | None = None
    active_diagnosis: str | None = None
    treatment_plan: str | None = None
    pending_orders: str | None = None
    medication_due: str | None = None
    abnormal_vitals: str | None = None
    critical_alerts: str | None = None
    discharge_tasks: str | None = None
    special_instructions: str | None = None


class IPDHandoverRead(IPDHandoverCreate):
    id: UUID
    sender_user_id: UUID
    handed_over_at: datetime
    acknowledged_at: datetime | None = None
    status: str

    model_config = {"from_attributes": True}


class IPDHandoverBoardRead(IPDHandoverRead):
    admission_id: UUID
    admission_number: str | None = None
    patient_name: str | None = None
    ward_name: str | None = None
    bed_number: str | None = None


class IPDTimelineEventRead(BaseModel):
    id: UUID
    event_type: str
    title: str
    detail: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    occurred_at: datetime
    actor_user_id: UUID | None = None

    model_config = {"from_attributes": True}


class IPDPatientWorkspace(BaseModel):
    admission: IPDAdmissionRead
    assignments: list[IPDStaffAssignmentRead]
    clinical_notes: list[IPDClinicalNoteRead]
    nursing_notes: list[IPDNursingNoteRead]
    orders: list[IPDOrderRead]
    medications: list[IPDMedicationAdministrationRead]
    nursing_tasks: list[IPDNursingTaskRead]
    handovers: list[IPDHandoverRead]
    timeline: list[IPDTimelineEventRead]


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
