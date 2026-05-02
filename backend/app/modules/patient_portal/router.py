from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_patient_account_or_superadmin_demo
from app.modules.patient_portal.service import PatientPortalService
from app.schemas.portal import PatientAppointmentCreate, PatientAppointmentRead, PatientAppointmentStatusUpdate, PatientPortalOverviewRead

router = APIRouter(prefix="/portal", tags=["Patient Portal"])


@router.get("/overview", response_model=PatientPortalOverviewRead)
def portal_overview(user=Depends(get_current_patient_account_or_superadmin_demo), db: Session = Depends(get_db)) -> PatientPortalOverviewRead:
    return PatientPortalService(db).get_overview(user)


@router.get("/appointments", response_model=list[PatientAppointmentRead])
def list_patient_appointments(user=Depends(get_current_patient_account_or_superadmin_demo), db: Session = Depends(get_db)) -> list[PatientAppointmentRead]:
    return PatientPortalService(db).list_appointments(user)


@router.post("/appointments", response_model=PatientAppointmentRead)
def create_patient_appointment(
    payload: PatientAppointmentCreate,
    user=Depends(get_current_patient_account_or_superadmin_demo),
    db: Session = Depends(get_db),
) -> PatientAppointmentRead:
    return PatientPortalService(db).create_appointment(payload, user)


@router.put("/appointments/{appointment_id}/status", response_model=PatientAppointmentRead)
def update_patient_appointment_status(
    appointment_id: UUID,
    payload: PatientAppointmentStatusUpdate,
    user=Depends(get_current_patient_account_or_superadmin_demo),
    db: Session = Depends(get_db),
) -> PatientAppointmentRead:
    return PatientPortalService(db).update_appointment_status(appointment_id, payload.status, user)
