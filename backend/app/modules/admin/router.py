from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.admin.service import AdminService
from app.schemas.role import RoleRead, RoleUpdatePermissions
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(require_permissions("settings.user.manage"))])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    return [UserRead.model_validate(item, from_attributes=True) for item in AdminService(db).list_users()]


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_permissions("settings.user.manage"))])
def create_user(
    payload: UserCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    created = AdminService(db).create_user(payload, user.id, context)
    return UserRead.model_validate(created, from_attributes=True)


@router.get("/roles", response_model=list[RoleRead], dependencies=[Depends(require_permissions("settings.role.manage"))])
def list_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    return [RoleRead.model_validate(item, from_attributes=True) for item in AdminService(db).list_roles()]


@router.put("/roles/{code}/permissions", response_model=RoleRead, dependencies=[Depends(require_permissions("settings.role.manage"))])
def update_role_permissions(
    code: str,
    payload: RoleUpdatePermissions,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleRead:
    role = AdminService(db).update_role_permissions(code, payload, user.id, context)
    return RoleRead.model_validate(role, from_attributes=True)

