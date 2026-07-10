from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.appointments.service import AppointmentsService
from app.schemas.appointment import (
    AppointmentCheckInRequest,
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    DoctorOPDScheduleRead,
    DoctorOPDScheduleUpsert,
    DoctorSlotsResponse,
)
from app.schemas.encounter import OPDVisitRead

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("", response_model=list[AppointmentRead], dependencies=[Depends(require_permissions("appointment.view"))])
def list_appointments(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AppointmentRead]:
    return AppointmentsService(db).list_appointments(user)


@router.post("", response_model=AppointmentRead, dependencies=[Depends(require_permissions("appointment.book"))])
def create_appointment(
    payload: AppointmentCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentsService(db).create_appointment(payload, user)


@router.get("/doctor-schedules", response_model=list[DoctorOPDScheduleRead], dependencies=[Depends(require_permissions("opd.view"))])
def list_doctor_schedules(
    doctor_user_id: UUID | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DoctorOPDScheduleRead]:
    return AppointmentsService(db).list_doctor_schedules(user, doctor_user_id)


@router.post("/doctor-schedules", response_model=DoctorOPDScheduleRead, dependencies=[Depends(require_permissions("settings.user.manage"))])
def upsert_doctor_schedule(
    payload: DoctorOPDScheduleUpsert,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DoctorOPDScheduleRead:
    return AppointmentsService(db).upsert_doctor_schedule(payload, user)


@router.get(
    "/doctor-slots",
    response_model=DoctorSlotsResponse,
    dependencies=[Depends(require_any_permissions("opd.view", "appointment.book", "telemedicine.view", "telemedicine.appointment.create"))],
)
def get_doctor_slots(
    doctor_user_id: UUID,
    slot_date: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DoctorSlotsResponse:
    return AppointmentsService(db).get_doctor_slots(doctor_user_id, date.fromisoformat(slot_date), user)


@router.put("/{appointment_id}", response_model=AppointmentRead, dependencies=[Depends(require_permissions("appointment.manage"))])
def update_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentsService(db).update_appointment(appointment_id, payload, user)


@router.put("/{appointment_id}/status", response_model=AppointmentRead, dependencies=[Depends(require_permissions("appointment.manage"))])
def update_appointment_status(
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentsService(db).update_status(appointment_id, payload.status, user)


@router.post("/{appointment_id}/check-in", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("appointment.manage"))])
def check_in_appointment(
    appointment_id: UUID,
    payload: AppointmentCheckInRequest,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = AppointmentsService(db).check_in_to_opd(appointment_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)
