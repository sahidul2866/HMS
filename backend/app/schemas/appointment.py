from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    patient_id: UUID
    doctor_user_id: UUID
    appointment_at: datetime
    reason: str | None = None
    note: str | None = None


class AppointmentRead(BaseModel):
    id: UUID
    appointment_number: str
    patient_id: UUID
    patient_name: str
    doctor_user_id: UUID
    doctor_name: str
    appointment_at: datetime
    status: str
    reason: str | None = None
    note: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(scheduled|confirmed|checked_in|completed|cancelled)$")


class AppointmentCheckInRequest(BaseModel):
    department_name: str = Field(min_length=2, max_length=120)
    consultation_fee: float = Field(default=0, ge=0)
    chief_complaint: str | None = None
    note: str | None = None
