from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.patient import PatientClinicalHistoryRead
from app.schemas.user import UserRead


class PatientAppointmentCreate(BaseModel):
    doctor_user_id: UUID
    appointment_at: datetime
    reason: str = Field(min_length=3, max_length=500)
    note: str | None = None


class PatientAppointmentRead(BaseModel):
    id: UUID
    appointment_number: str
    doctor_user_id: UUID
    doctor_name: str
    appointment_at: datetime
    status: str
    reason: str | None = None
    note: str | None = None


class PatientAppointmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(cancelled)$")


class PatientPortalOverviewRead(BaseModel):
    patient: PatientClinicalHistoryRead
    appointments: list[PatientAppointmentRead]
    doctors: list[UserRead]
