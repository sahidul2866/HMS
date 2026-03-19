from datetime import date
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

