from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.appointments.service import AppointmentsService
from app.schemas.appointment import AppointmentCheckInRequest, AppointmentRead, AppointmentStatusUpdate
from app.schemas.encounter import OPDVisitRead

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("", response_model=list[AppointmentRead], dependencies=[Depends(require_permissions("appointment.view"))])
def list_appointments(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AppointmentRead]:
    return AppointmentsService(db).list_appointments(user)


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
