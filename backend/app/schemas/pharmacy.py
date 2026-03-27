from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PharmacyDispenseCreate(BaseModel):
    patient_id: UUID | None = None
    branch_id: UUID | None = None
    source_visit_id: UUID | None = None
    source_visit_order_id: UUID | None = None
    prescription_ref: str | None = None
    medicine_name: str = Field(min_length=2, max_length=150)
    quantity: Decimal
    unit_price: Decimal
    note: str | None = None


class PharmacyDispenseReturnCreate(BaseModel):
    quantity: Decimal = Field(gt=0)
    note: str | None = None


class PharmacyDispenseRead(BaseModel):
    id: UUID
    patient_id: UUID | None = None
    source_visit_id: UUID | None = None
    source_visit_order_id: UUID | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    visit_number: str | None = None
    medicine_name: str
    requested_quantity: Decimal | None = None
    quantity: Decimal
    returned_quantity: Decimal
    remaining_quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    status: str
    prescription_ref: str | None = None
    note: str | None = None
    return_note: str | None = None
    dispensed_at: str
    dispensed_by_name: str | None = None

    model_config = {"from_attributes": True}


class PharmacyPendingPrescriptionRead(BaseModel):
    order_id: UUID
    visit_id: UUID
    visit_number: str
    patient_id: UUID
    patient_number: str
    patient_name: str
    doctor_name: str
    visit_date: str
    visit_status: str
    item_name: str
    quantity: Decimal
    dispensed_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("0")
    instructions: str | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None


class PharmacySummaryRead(BaseModel):
    total_dispenses: int
    today_dispenses: int
    pending_prescriptions: int
    billed_prescriptions: int
    partial_dispenses: int
    returned_dispenses: int
