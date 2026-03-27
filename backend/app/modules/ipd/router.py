from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.ipd.service import IPDService
from app.schemas.encounter import IPDAdmissionCreate, IPDAdmissionRead, IPDBedCreate, IPDBedRead, IPDDischarge, IPDTransfer, IPDSummary

router = APIRouter(prefix="/ipd", tags=["IPD"])


@router.get("/admissions", response_model=list[IPDAdmissionRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_admissions(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDAdmissionRead]:
    return [IPDAdmissionRead.model_validate(item, from_attributes=True) for item in IPDService(db).list_admissions(user)]


@router.get("/admissions/{admission_id}", response_model=IPDAdmissionRead, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_admission(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDAdmissionRead:
    admission = IPDService(db).get_admission(admission_id, user)
    return IPDAdmissionRead.model_validate(admission, from_attributes=True)


@router.get("/summary", response_model=IPDSummary, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDSummary:
    return IPDService(db).get_summary(user)


@router.get("/beds", response_model=list[IPDBedRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_beds(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDBedRead]:
    return [IPDBedRead.model_validate(item, from_attributes=True) for item in IPDService(db).list_beds(user)]


@router.post("/beds", response_model=IPDBedRead, dependencies=[Depends(require_permissions("ipd.bed.manage"))])
def create_ipd_bed(
    payload: IPDBedCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDBedRead:
    bed = IPDService(db).create_bed(payload, user, context)
    return IPDBedRead.model_validate(bed, from_attributes=True)


@router.post("/admissions", response_model=IPDAdmissionRead, dependencies=[Depends(require_permissions("ipd.admission.manage"))])
def create_ipd_admission(
    payload: IPDAdmissionCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = IPDService(db).create_admission(payload, user, context)
    return IPDAdmissionRead.model_validate(admission, from_attributes=True)


@router.put(
    "/admissions/{admission_id}/discharge",
    response_model=IPDAdmissionRead,
    dependencies=[Depends(require_permissions("ipd.admission.manage"))],
)
def discharge_ipd_admission(
    admission_id: UUID,
    payload: IPDDischarge,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = IPDService(db).discharge(admission_id, payload, user, context)
    return IPDAdmissionRead.model_validate(admission, from_attributes=True)


@router.put(
    "/admissions/{admission_id}/transfer",
    response_model=IPDAdmissionRead,
    dependencies=[Depends(require_permissions("ipd.admission.manage"))],
)
def transfer_ipd_admission(
    admission_id: UUID,
    payload: IPDTransfer,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = IPDService(db).transfer(admission_id, payload, user, context)
    return IPDAdmissionRead.model_validate(admission, from_attributes=True)
