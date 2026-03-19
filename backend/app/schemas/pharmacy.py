from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PharmacyDispenseCreate(BaseModel):
    patient_id: UUID | None = None
    branch_id: UUID | None = None
    prescription_ref: str | None = None
    medicine_name: str = Field(min_length=2, max_length=150)
    quantity: Decimal
    unit_price: Decimal
    note: str | None = None


class PharmacyDispenseRead(BaseModel):
    id: UUID
    medicine_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    prescription_ref: str | None = None

    model_config = {"from_attributes": True}

