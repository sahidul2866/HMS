from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions
from app.modules.radiology.service import RadiologyService
from app.schemas.encounter import ClinicalInvestigationResultUpdate, ClinicalInvestigationWorkItemRead
from app.schemas.radiology import RadiologySummaryRead

router = APIRouter(prefix="/radiology", tags=["Radiology"])


@router.get(
    "/summary",
    response_model=RadiologySummaryRead,
    dependencies=[Depends(require_any_permissions("radiology.view", "radiology.manage"))],
)
def get_radiology_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> RadiologySummaryRead:
    return RadiologyService(db).get_summary(user)


@router.get(
    "/worklist",
    response_model=list[ClinicalInvestigationWorkItemRead],
    dependencies=[Depends(require_any_permissions("radiology.view", "radiology.manage"))],
)
def list_radiology_worklist(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[ClinicalInvestigationWorkItemRead]:
    return RadiologyService(db).list_worklist(user)


@router.put(
    "/worklist/{order_id}",
    response_model=ClinicalInvestigationWorkItemRead,
    dependencies=[Depends(require_any_permissions("radiology.manage", "settings.role.manage"))],
)
def update_radiology_result(
    order_id: UUID,
    payload: ClinicalInvestigationResultUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClinicalInvestigationWorkItemRead:
    return RadiologyService(db).update_result(order_id, payload, user, context)
