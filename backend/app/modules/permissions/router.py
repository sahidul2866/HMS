from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.permissions import require_any_permissions
from app.modules.permissions.service import PermissionsService
from app.schemas.permission import PermissionRead

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get(
    "",
    response_model=list[PermissionRead],
    dependencies=[Depends(require_any_permissions("settings.permission.manage", "settings.role.manage"))],
)
def list_permissions(db: Session = Depends(get_db)) -> list[PermissionRead]:
    return [PermissionRead.model_validate(item, from_attributes=True) for item in PermissionsService(db).list_permissions()]
