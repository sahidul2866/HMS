from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.patients.service import PatientsService
from app.schemas.patient import PatientCreate, PatientRead

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=list[PatientRead], dependencies=[Depends(require_permissions("patient.view"))])
def list_patients(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PatientRead]:
    return [PatientRead.model_validate(item, from_attributes=True) for item in PatientsService(db).list_patients(user)]


@router.get("/{patient_id}", response_model=PatientRead, dependencies=[Depends(require_permissions("patient.view"))])
def get_patient(patient_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientRead:
    patient = PatientsService(db).get_patient(patient_id, user)
    return PatientRead.model_validate(patient, from_attributes=True)


@router.post("", response_model=PatientRead, dependencies=[Depends(require_permissions("patient.create"))])
def create_patient(
    payload: PatientCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientRead:
    patient = PatientsService(db).create_patient(payload, user, context)
    return PatientRead.model_validate(patient, from_attributes=True)

