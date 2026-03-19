from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.permissions import require_permissions
from app.modules.audit.service import AuditService
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=list[AuditLogRead], dependencies=[Depends(require_permissions("audit.view"))])
def list_logs(db: Session = Depends(get_db)) -> list[AuditLogRead]:
    return [AuditLogRead.model_validate(item, from_attributes=True) for item in AuditService(db).list_logs()]

