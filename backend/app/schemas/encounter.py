from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.patient import PatientRead


class OPDVisitCreate(BaseModel):
    patient_id: UUID
    visit_date: date
    department_name: str = Field(min_length=2, max_length=120)
    doctor_user_id: UUID | None = None
    consulting_doctor_name: str = Field(min_length=2, max_length=150)
    chief_complaint: str | None = None
    consultation_fee: Decimal = Field(default=0, ge=0)
    note: str | None = None


class OPDVisitStatusUpdate(BaseModel):
    status: str = Field(pattern="^(waiting|in_consultation|completed|cancelled)$")


class OPDVisitOrderCreate(BaseModel):
    order_type: str = Field(pattern="^(prescription|investigation)$")
    service_area: str | None = Field(default=None, pattern="^(laboratory|radiology)$")
    item_name: str = Field(min_length=2, max_length=180)
    instructions: str | None = None
    quantity: Decimal = Field(default=1, ge=0.01)

    @model_validator(mode="after")
    def validate_service_area(self) -> "OPDVisitOrderCreate":
        if self.order_type == "investigation" and not self.service_area:
            raise ValueError("Investigation orders require a service area")
        if self.order_type == "prescription":
            self.service_area = None
        return self


class OPDVisitOrderRead(OPDVisitOrderCreate):
    id: UUID
    status: str
    result_text: str | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OPDVisitRead(OPDVisitCreate):
    id: UUID
    visit_number: str
    status: str
    consulting_doctor_user_id: UUID | None = None
    converted_ipd_admission_id: UUID | None = None
    patient: PatientRead
    orders: list[OPDVisitOrderRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class OPDSummary(BaseModel):
    total_visits: int
    waiting_visits: int
    in_consultation_visits: int
    completed_visits: int


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
    discharge_note: str | None = None


class IPDAdmissionRead(IPDAdmissionCreate):
    id: UUID
    admission_number: str
    attending_doctor_user_id: UUID | None = None
    status: str
    discharged_at: datetime | None = None
    discharge_note: str | None = None
    patient: PatientRead
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
    patient_name: str
    consulting_doctor_name: str
    service_area: str
    item_name: str
    quantity: Decimal
    instructions: str | None = None
    status: str
    result_text: str | None = None
    completed_at: datetime | None = None


class ClinicalInvestigationResultUpdate(BaseModel):
    status: str = Field(pattern="^(in_progress|completed|cancelled)$")
    result_text: str | None = None
