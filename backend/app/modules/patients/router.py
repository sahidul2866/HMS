from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.patients.service import PatientsService
from app.schemas.encounter import OPDVisitRead
from app.schemas.patient import (
    PatientClinicalHistoryRead,
    PatientCreate,
    PatientIdCardRead,
    PatientIdCardTemplateRead,
    PatientIdCardTemplateWrite,
    PatientLookupResult,
    PatientMobileLookupRead,
    PatientRead,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=list[PatientRead], dependencies=[Depends(require_permissions("patient.view"))])
def list_patients(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PatientRead]:
    return [PatientRead.model_validate(item, from_attributes=True) for item in PatientsService(db).list_patients(user)]


@router.get("/search", response_model=list[PatientLookupResult], dependencies=[Depends(require_permissions("patient.view"))])
def search_patients(
    q: str,
    limit: int = 10,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PatientLookupResult]:
    return PatientsService(db).search_patients(q, user, limit=min(max(limit, 1), 25))


@router.get("/by-mobile", response_model=PatientMobileLookupRead, dependencies=[Depends(require_permissions("patient.view"))])
def lookup_patients_by_mobile(
    mobile: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientMobileLookupRead:
    return PatientsService(db).lookup_patients_by_mobile(mobile, user)


@router.get("/{patient_id}", response_model=PatientRead, dependencies=[Depends(require_permissions("patient.view"))])
def get_patient(patient_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientRead:
    patient = PatientsService(db).get_patient(patient_id, user)
    return PatientRead.model_validate(patient, from_attributes=True)


@router.get("/{patient_id}/history", response_model=PatientClinicalHistoryRead, dependencies=[Depends(require_permissions("patient.view"))])
def get_patient_history(patient_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientClinicalHistoryRead:
    return PatientsService(db).get_clinical_history(patient_id, user)


@router.get("/{patient_id}/id-card", response_model=PatientIdCardRead, dependencies=[Depends(require_permissions("patient.id_card.view"))])
def get_patient_id_card(patient_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientIdCardRead:
    return PatientsService(db).get_id_card(patient_id, user, context)


@router.post("/{patient_id}/id-card/generate", response_model=PatientIdCardRead, dependencies=[Depends(require_permissions("patient.id_card.generate"))])
def generate_patient_id_card(patient_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientIdCardRead:
    return PatientsService(db).generate_id_card(patient_id, user, context)


@router.post("/{patient_id}/id-card/print", response_model=PatientIdCardRead, dependencies=[Depends(require_permissions("patient.id_card.print"))])
def print_patient_id_card(patient_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientIdCardRead:
    return PatientsService(db).print_id_card(patient_id, user, context)


@router.post("/{patient_id}/id-card/reprint", response_model=PatientIdCardRead, dependencies=[Depends(require_permissions("patient.id_card.reprint"))])
def reprint_patient_id_card(patient_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientIdCardRead:
    return PatientsService(db).print_id_card(patient_id, user, context, reprint=True)


@router.get("/id-card/template", response_model=PatientIdCardTemplateRead, dependencies=[Depends(require_permissions("patient.id_card.configure"))])
def get_patient_id_card_template(user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientIdCardTemplateRead:
    return PatientsService(db).get_id_card_template(user)


@router.put("/id-card/template", response_model=PatientIdCardTemplateRead, dependencies=[Depends(require_permissions("patient.id_card.configure"))])
def update_patient_id_card_template(payload: PatientIdCardTemplateWrite, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PatientIdCardTemplateRead:
    return PatientsService(db).update_id_card_template(payload, user, context)


@router.get("/{patient_id}/opd-visits", response_model=list[OPDVisitRead], dependencies=[Depends(require_permissions("opd.view"))])
def get_patient_opd_visits(patient_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[OPDVisitRead]:
    return [OPDVisitRead.model_validate(visit, from_attributes=True) for visit in PatientsService(db).get_patient_opd_visits(patient_id, user)]


@router.post("", response_model=PatientRead, dependencies=[Depends(require_permissions("patient.create"))])
def create_patient(
    payload: PatientCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientRead:
    patient = PatientsService(db).create_patient(payload, user, context)
    return PatientRead.model_validate(patient, from_attributes=True)
