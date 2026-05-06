from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.role import Role
from app.modules.audit.service import AuditService
from app.modules.roles.repository import RolesRepository
from app.schemas.role import RoleCreate, RoleUpdatePermissions
from app.utils.enums import AuditAction


class RolesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = RolesRepository(db)

    def list_roles(self) -> list[Role]:
        return self.repository.list_roles()

    def create_role(self, payload: RoleCreate, actor_id=None, context: dict[str, str | None] | None = None) -> Role:
        role = Role(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            is_doctor_role=payload.is_doctor_role,
            is_referral_role=payload.is_referral_role,
        )
        role.permissions = self.repository.get_permissions(payload.permission_codes)
        self.repository.create_role(role)
        if actor_id and context is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                action=AuditAction.ROLE_CREATE,
                module="admin",
                entity_type="role",
                entity_id=str(role.id),
                detail={"role_code": role.code, "permissions": payload.permission_codes},
                context=context,
            )
        self.db.commit()
        self.db.refresh(role)
        return role

    def update_role_permissions(self, code: str, payload: RoleUpdatePermissions, actor_id, context: dict[str, str | None]) -> Role:
        role = self.repository.get_role_by_code(code)
        if not role:
            raise AppException(404, "role_not_found", "Role not found")
        role.permissions = self.repository.get_permissions(payload.permission_codes)
        AuditService(self.db).log(
            user_id=actor_id,
            action=AuditAction.ROLE_PERMISSION_UPDATE,
            module="admin",
            entity_type="role",
            entity_id=str(role.id),
            detail={"role_code": role.code, "permissions": payload.permission_codes},
            context=context,
        )
        self.db.commit()
        self.db.refresh(role)
        return role
