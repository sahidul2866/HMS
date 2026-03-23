from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.opd.service import OPDService
from app.schemas.encounter import IPDAdmissionRead, OPDConvertToIPD, OPDSummary, OPDVisitCreate, OPDVisitOrderCreate, OPDVisitRead, OPDVisitStatusUpdate

router = APIRouter(prefix="/opd", tags=["OPD"])


@router.get("/visits", response_model=list[OPDVisitRead], dependencies=[Depends(require_permissions("opd.view"))])
def list_opd_visits(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[OPDVisitRead]:
    return [OPDVisitRead.model_validate(item, from_attributes=True) for item in OPDService(db).list_visits(user)]


@router.get("/summary", response_model=OPDSummary, dependencies=[Depends(require_permissions("opd.view"))])
def get_opd_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> OPDSummary:
    return OPDService(db).get_summary(user)


@router.post("/visits", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.visit.manage"))])
def create_opd_visit(
    payload: OPDVisitCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).create_visit(payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.put(
    "/visits/{visit_id}/status",
    response_model=OPDVisitRead,
    dependencies=[Depends(require_any_permissions("opd.visit.manage", "opd.view"))],
)
def update_opd_status(
    visit_id: UUID,
    payload: OPDVisitStatusUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).update_status(visit_id, payload.status, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.post("/visits/{visit_id}/orders", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.visit.manage"))])
def create_opd_order(
    visit_id: UUID,
    payload: OPDVisitOrderCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).create_order(visit_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.post(
    "/visits/{visit_id}/convert-to-ipd",
    response_model=IPDAdmissionRead,
    dependencies=[Depends(require_permissions("ipd.admission.manage"))],
)
def convert_opd_to_ipd(
    visit_id: UUID,
    payload: OPDConvertToIPD,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = OPDService(db).convert_to_ipd(visit_id, payload, user, context)
    return IPDAdmissionRead.model_validate(admission, from_attributes=True)
