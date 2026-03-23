from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.reporting.service import ReportingService
from app.schemas.reporting import ClinicalOperationsSummaryRead

router = APIRouter(prefix="/reporting", tags=["Reporting"])


@router.get("/clinical-summary", response_model=ClinicalOperationsSummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_clinical_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> ClinicalOperationsSummaryRead:
    return ReportingService(db).get_clinical_summary(user)
