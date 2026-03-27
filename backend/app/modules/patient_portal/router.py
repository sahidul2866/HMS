from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.patient_portal.service import PatientPortalService
from app.schemas.portal import PatientAppointmentCreate, PatientAppointmentRead, PatientAppointmentStatusUpdate, PatientPortalOverviewRead

router = APIRouter(prefix="/portal", tags=["Patient Portal"])


@router.get("/overview", response_model=PatientPortalOverviewRead, dependencies=[Depends(require_permissions("patient.portal.view"))])
def portal_overview(user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientPortalOverviewRead:
    return PatientPortalService(db).get_overview(user)


@router.get("/appointments", response_model=list[PatientAppointmentRead], dependencies=[Depends(require_permissions("appointment.view"))])
def list_patient_appointments(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PatientAppointmentRead]:
    return PatientPortalService(db).list_appointments(user)


@router.post("/appointments", response_model=PatientAppointmentRead, dependencies=[Depends(require_permissions("appointment.book"))])
def create_patient_appointment(
    payload: PatientAppointmentCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientAppointmentRead:
    return PatientPortalService(db).create_appointment(payload, user)


@router.put("/appointments/{appointment_id}/status", response_model=PatientAppointmentRead, dependencies=[Depends(require_permissions("appointment.book"))])
def update_patient_appointment_status(
    appointment_id: UUID,
    payload: PatientAppointmentStatusUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientAppointmentRead:
    return PatientPortalService(db).update_appointment_status(appointment_id, payload.status, user)
