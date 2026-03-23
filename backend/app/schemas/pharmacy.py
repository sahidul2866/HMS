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


class PharmacyDispenseRead(BaseModel):
    id: UUID
    patient_id: UUID | None = None
    source_visit_id: UUID | None = None
    source_visit_order_id: UUID | None = None
    medicine_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    prescription_ref: str | None = None

    model_config = {"from_attributes": True}


class PharmacyPendingPrescriptionRead(BaseModel):
    order_id: UUID
    visit_id: UUID
    visit_number: str
    patient_id: UUID
    patient_name: str
    doctor_name: str
    item_name: str
    quantity: Decimal
    instructions: str | None = None
