from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.roles.service import RolesService
from app.schemas.role import RoleCreate, RoleRead, RoleUpdatePermissions

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleRead], dependencies=[Depends(require_permissions("settings.role.manage"))])
def list_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    return [RoleRead.model_validate(role, from_attributes=True) for role in RolesService(db).list_roles()]


@router.post("", response_model=RoleRead, dependencies=[Depends(require_permissions("settings.role.manage"))])
def create_role(
    payload: RoleCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleRead:
    return RoleRead.model_validate(RolesService(db).create_role(payload, user.id, context), from_attributes=True)


@router.put("/{code}/permissions", response_model=RoleRead, dependencies=[Depends(require_permissions("settings.role.manage"))])
def update_role_permissions(
    code: str,
    payload: RoleUpdatePermissions,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleRead:
    role = RolesService(db).update_role_permissions(code, payload, user.id, context)
    return RoleRead.model_validate(role, from_attributes=True)
