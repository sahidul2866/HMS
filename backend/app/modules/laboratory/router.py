from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions
from app.modules.laboratory.service import LaboratoryService
from app.schemas.encounter import ClinicalInvestigationResultUpdate, ClinicalInvestigationWorkItemRead
from app.schemas.laboratory import LaboratorySummaryRead

router = APIRouter(prefix="/laboratory", tags=["Laboratory"])


@router.get(
    "/summary",
    response_model=LaboratorySummaryRead,
    dependencies=[Depends(require_any_permissions("laboratory.view", "laboratory.manage"))],
)
def get_laboratory_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> LaboratorySummaryRead:
    return LaboratoryService(db).get_summary(user)


@router.get(
    "/worklist",
    response_model=list[ClinicalInvestigationWorkItemRead],
    dependencies=[Depends(require_any_permissions("laboratory.view", "laboratory.manage"))],
)
def list_laboratory_worklist(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[ClinicalInvestigationWorkItemRead]:
    return LaboratoryService(db).list_worklist(user)


@router.put(
    "/worklist/{order_id}",
    response_model=ClinicalInvestigationWorkItemRead,
    dependencies=[Depends(require_any_permissions("laboratory.manage", "settings.role.manage"))],
)
def update_laboratory_result(
    order_id: UUID,
    payload: ClinicalInvestigationResultUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClinicalInvestigationWorkItemRead:
    return LaboratoryService(db).update_result(order_id, payload, user, context)
