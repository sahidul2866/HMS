from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.admin.service import AdminService
from app.modules.patient_auth.service import PatientAuthService
from app.schemas.auth import PatientPortalAccountCreate, PatientPortalAccountRead
from app.schemas.role import RoleCreate, RoleRead, RoleUpdatePermissions
from app.schemas.scope import EffectiveAccessRead, RoleScopeCreate, RoleScopeRead, UserScopeCreate, UserScopeRead
from app.schemas.user import UserCreate, UserOPDSettingsUpdate, UserRead

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


@router.post("/patient-portal-accounts", response_model=PatientPortalAccountRead, dependencies=[Depends(require_permissions("settings.user.manage"))])
def create_patient_portal_account(
    payload: PatientPortalAccountCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientPortalAccountRead:
    account = PatientAuthService(db).create_existing_patient_account(payload, actor_id=user.id)
    return PatientAuthService(db).to_current_patient(account)


@router.put("/users/{user_id}/opd-settings", response_model=UserRead, dependencies=[Depends(require_any_permissions("settings.user.manage", "opd.settings.manage"))])
def update_user_opd_settings(
    user_id: UUID,
    payload: UserOPDSettingsUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    updated = AdminService(db).update_user_opd_settings(user_id, payload, user.id, context)
    return UserRead.model_validate(updated, from_attributes=True)


@router.get("/roles", response_model=list[RoleRead], dependencies=[Depends(require_permissions("settings.role.manage"))])
def list_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    return [RoleRead.model_validate(item, from_attributes=True) for item in AdminService(db).list_roles()]


@router.post("/roles", response_model=RoleRead, dependencies=[Depends(require_permissions("settings.role.manage"))])
def create_role(
    payload: RoleCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleRead:
    role = AdminService(db).create_role(payload, user.id, context)
    return RoleRead.model_validate(role, from_attributes=True)


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


@router.get("/scopes/users", response_model=list[UserScopeRead], dependencies=[Depends(require_permissions("settings.scope.manage"))])
def list_user_scopes(user_id: UUID | None = None, db: Session = Depends(get_db)) -> list[UserScopeRead]:
    return [UserScopeRead.model_validate(item, from_attributes=True) for item in AdminService(db).list_user_scopes(user_id)]


@router.post("/scopes/users", response_model=UserScopeRead, dependencies=[Depends(require_permissions("settings.scope.manage"))])
def create_user_scope(
    payload: UserScopeCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserScopeRead:
    return UserScopeRead.model_validate(AdminService(db).create_user_scope(payload, user, context), from_attributes=True)


@router.delete("/scopes/users/{scope_id}", response_model=UserScopeRead, dependencies=[Depends(require_permissions("settings.scope.manage"))])
def deactivate_user_scope(
    scope_id: UUID,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserScopeRead:
    return UserScopeRead.model_validate(AdminService(db).deactivate_user_scope(scope_id, user, context), from_attributes=True)


@router.get("/scopes/roles", response_model=list[RoleScopeRead], dependencies=[Depends(require_permissions("settings.scope.manage"))])
def list_role_scopes(role_id: UUID | None = None, db: Session = Depends(get_db)) -> list[RoleScopeRead]:
    return [RoleScopeRead.model_validate(item, from_attributes=True) for item in AdminService(db).list_role_scopes(role_id)]


@router.post("/scopes/roles", response_model=RoleScopeRead, dependencies=[Depends(require_permissions("settings.scope.manage"))])
def create_role_scope(
    payload: RoleScopeCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleScopeRead:
    return RoleScopeRead.model_validate(AdminService(db).create_role_scope(payload, user, context), from_attributes=True)


@router.delete("/scopes/roles/{scope_id}", response_model=RoleScopeRead, dependencies=[Depends(require_permissions("settings.scope.manage"))])
def deactivate_role_scope(
    scope_id: UUID,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleScopeRead:
    return RoleScopeRead.model_validate(AdminService(db).deactivate_role_scope(scope_id, user, context), from_attributes=True)


@router.get("/users/{user_id}/effective-access", response_model=EffectiveAccessRead, dependencies=[Depends(require_permissions("settings.scope.manage"))])
def effective_access(user_id: UUID, db: Session = Depends(get_db)) -> EffectiveAccessRead:
    return AdminService(db).effective_access(user_id)
