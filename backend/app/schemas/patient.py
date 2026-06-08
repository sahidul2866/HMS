from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class PatientCreate(BaseModel):
    branch_id: UUID | None = None
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    phone: str | None = None
    email: EmailStr | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class PatientRead(BaseModel):
    id: UUID
    branch_id: UUID | None = None
    patient_number: str
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    model_config = {"from_attributes": True}


class PatientIdCardTemplateRead(BaseModel):
    card_size: str = "85.6x54mm"
    logo_url: str | None = None
    header: str = "Hospital Patient ID"
    footer: str = "Please present this card at every hospital visit."
    code_type: str = "code39"
    theme_color: str = "#0f766e"
    show_phone: bool = True
    show_emergency_contact: bool = True
    show_dob: bool = True
    show_issue_date: bool = True
    print_layout: str = "standard-card"


class PatientIdCardTemplateWrite(PatientIdCardTemplateRead):
    pass


class PatientIdCardRead(BaseModel):
    patient: PatientRead
    hospital_name: str
    scan_code: str
    code_type: str
    issue_date: date
    is_reprint: bool = False
    template: PatientIdCardTemplateRead


class PatientLookupResult(PatientRead):
    full_name: str


class PatientMobileLookupRead(BaseModel):
    mobile: str
    normalized_mobile: str
    max_patients_allowed: int
    current_patient_count: int
    can_add_more: bool
    patients: list[PatientLookupResult]


class PatientHistoryOrderRead(BaseModel):
    id: UUID
    order_type: str
    service_area: str | None = None
    item_name: str
    quantity: str
    status: str
    instructions: str | None = None
    result_text: str | None = None
    completed_at: datetime | None = None


class PatientHistoryOPDVisitRead(BaseModel):
    id: UUID
    visit_number: str
    visit_date: date
    department_name: str
    consulting_doctor_name: str
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
    status: str
    orders: list[PatientHistoryOrderRead]


class PatientHistoryIPDAdmissionRead(BaseModel):
    id: UUID
    admission_number: str
    admitted_at: datetime
    attending_doctor_name: str
    diagnosis: str | None = None
    status: str
    ward_name: str
    bed_number: str
    discharged_at: datetime | None = None
    active_doctors: list[str] = Field(default_factory=list)
    active_nurses: list[str] = Field(default_factory=list)
    tracking: list[dict[str, str | None]] = Field(default_factory=list)


class PatientHistoryBillingInvoiceRead(BaseModel):
    id: UUID
    invoice_number: str
    created_at: datetime
    status: str
    payment_status: str
    total_amount: str
    paid_amount: str
    due_amount: str
    referred_doctor_name: str | None = None


class PatientHistoryBillingPaymentRead(BaseModel):
    id: UUID
    invoice_number: str
    receipt_number: str
    payment_method: str
    amount: str
    received_at: datetime
    note: str | None = None


class PatientHistoryPharmacyDispenseRead(BaseModel):
    id: UUID
    prescription_ref: str | None = None
    medicine_name: str
    quantity: str
    total_price: str
    created_at: datetime


class PatientHistoryAppointmentRead(BaseModel):
    id: UUID
    appointment_number: str
    doctor_name: str
    appointment_at: datetime
    status: str
    reason: str | None = None
    note: str | None = None


class PatientClinicalHistoryRead(BaseModel):
    patient: PatientRead
    opd_visits: list[PatientHistoryOPDVisitRead]
    appointments: list[PatientHistoryAppointmentRead]
    ipd_admissions: list[PatientHistoryIPDAdmissionRead]
    billing_invoices: list[PatientHistoryBillingInvoiceRead]
    billing_payments: list[PatientHistoryBillingPaymentRead]
    pharmacy_dispenses: list[PatientHistoryPharmacyDispenseRead]
