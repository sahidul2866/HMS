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


class PatientRead(PatientCreate):
    id: UUID
    patient_number: str

    model_config = {"from_attributes": True}


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


class PatientHistoryBillingInvoiceRead(BaseModel):
    id: UUID
    invoice_number: str
    created_at: datetime
    status: str
    total_amount: str
    referred_doctor_name: str | None = None


class PatientHistoryPharmacyDispenseRead(BaseModel):
    id: UUID
    prescription_ref: str | None = None
    medicine_name: str
    quantity: str
    total_price: str
    created_at: datetime


class PatientClinicalHistoryRead(BaseModel):
    patient: PatientRead
    opd_visits: list[PatientHistoryOPDVisitRead]
    ipd_admissions: list[PatientHistoryIPDAdmissionRead]
    billing_invoices: list[PatientHistoryBillingInvoiceRead]
    pharmacy_dispenses: list[PatientHistoryPharmacyDispenseRead]
