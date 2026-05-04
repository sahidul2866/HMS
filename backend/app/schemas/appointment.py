from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    patient_id: UUID
    doctor_user_id: UUID
    appointment_at: datetime | None = None
    slot_start_at: datetime | None = None
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
    slot_start_at: datetime | None = None
    status: str
    reason: str | None = None
    note: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(scheduled|confirmed|checked_in|completed|cancelled)$")


class AppointmentUpdate(BaseModel):
    doctor_user_id: UUID
    slot_start_at: datetime
    reason: str | None = None
    note: str | None = None


class AppointmentCheckInRequest(BaseModel):
    department_name: str = Field(min_length=2, max_length=120)
    consultation_fee: float = Field(default=0, ge=0)
    chief_complaint: str | None = None
    note: str | None = None


class DoctorOPDScheduleUpsert(BaseModel):
    doctor_user_id: UUID
    weekday: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    slot_duration_minutes: int = Field(default=15, ge=5, le=180)
    buffer_minutes: int = Field(default=0, ge=0, le=60)


class DoctorOPDScheduleRead(DoctorOPDScheduleUpsert):
    id: UUID

    model_config = {"from_attributes": True}


class DoctorSlotAvailability(BaseModel):
    slot_start_at: datetime
    slot_end_at: datetime
    status: str  # available|booked
    source_type: str | None = None


class DoctorSlotsResponse(BaseModel):
    doctor_user_id: UUID
    date: date
    slot_duration_minutes: int
    buffer_minutes: int
    slots: list[DoctorSlotAvailability]
