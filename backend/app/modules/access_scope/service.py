from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.role import Role
from app.models.scope import RoleScope, UserScope
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.auth.service import AuthService
from app.schemas.scope import EffectiveAccessRead, RoleScopeCreate, UserScopeCreate


SCOPE_MANAGE_PERMISSION = "settings.scope.manage"
SCOPE_OVERRIDE_PERMISSION = "scope.override"

SUPERVISOR_PERMISSIONS = {
    "ward": ("ipd.assign_nurse", "ipd.assign_doctor", "ipd.settings.manage"),
    "doctor_profile": ("opd.view.doctor_wise", "opd.settings.manage"),
    "store": ("inventory.store.manage", "inventory.manage"),
    "queue_counter": ("queue.counter.manage", "queue.display.manage"),
    "queue_scope": ("queue.counter.manage", "queue.display.manage"),
    "lab_section": ("laboratory.manage",),
    "radiology_unit": ("radiology.manage",),
    "blood_bank_unit": ("blood_bank.report.export",),
}


class AccessScopeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth = AuthService(db)

    def list_user_scopes(self, user_id: UUID | None = None) -> list[UserScope]:
        stmt = select(UserScope).order_by(UserScope.scope_type, UserScope.scope_value, UserScope.created_at.desc())
        if user_id:
            stmt = stmt.where(UserScope.user_id == user_id)
        return list(self.db.scalars(stmt))

    def list_role_scopes(self, role_id: UUID | None = None) -> list[RoleScope]:
        stmt = select(RoleScope).order_by(RoleScope.scope_type, RoleScope.scope_value, RoleScope.created_at.desc())
        if role_id:
            stmt = stmt.where(RoleScope.role_id == role_id)
        return list(self.db.scalars(stmt))

    def create_user_scope(self, payload: UserScopeCreate, actor: User, context: dict[str, str | None]) -> UserScope:
        item = UserScope(branch_id=actor.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self.db.flush()
        self._audit(actor, "scope.user.assigned", "user_scope", item.id, payload.model_dump(mode="json"), context)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_role_scope(self, payload: RoleScopeCreate, actor: User, context: dict[str, str | None]) -> RoleScope:
        data = payload.model_dump()
        data.pop("is_temporary", None)
        data.pop("is_override", None)
        item = RoleScope(branch_id=actor.branch_id, **data, created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self.db.flush()
        self._audit(actor, "scope.role.assigned", "role_scope", item.id, payload.model_dump(mode="json"), context)
        self.db.commit()
        self.db.refresh(item)
        return item

    def deactivate_user_scope(self, scope_id: UUID, actor: User, context: dict[str, str | None]) -> UserScope:
        item = self.db.get(UserScope, scope_id)
        if not item:
            raise AppException(404, "scope_not_found", "User scope assignment was not found")
        item.is_active = False
        item.status = "inactive"
        item.updated_by = actor.id
        self._audit(actor, "scope.user.removed", "user_scope", item.id, {"scope_type": item.scope_type, "scope_value": item.scope_value}, context)
        self.db.commit()
        self.db.refresh(item)
        return item

    def deactivate_role_scope(self, scope_id: UUID, actor: User, context: dict[str, str | None]) -> RoleScope:
        item = self.db.get(RoleScope, scope_id)
        if not item:
            raise AppException(404, "scope_not_found", "Role scope assignment was not found")
        item.is_active = False
        item.status = "inactive"
        item.updated_by = actor.id
        self._audit(actor, "scope.role.removed", "role_scope", item.id, {"scope_type": item.scope_type, "scope_value": item.scope_value}, context)
        self.db.commit()
        self.db.refresh(item)
        return item

    def effective_access(self, user_id: UUID) -> EffectiveAccessRead:
        user = self.db.get(User, user_id)
        if not user:
            raise AppException(404, "user_not_found", "User not found")
        permissions = self.auth.get_effective_permissions(user)
        user_scopes = self.active_user_scopes(user)
        role_scopes = self.active_role_scopes(user)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for scope in [*user_scopes, *role_scopes]:
            grouped[scope.scope_type].append(self._scope_payload(scope))
        return EffectiveAccessRead(
            user_id=user.id,
            roles=[{"id": str(role.id), "code": role.code, "name": role.name} for role in user.roles],
            permissions=permissions,
            user_scopes=user_scopes,
            role_scopes=role_scopes,
            effective_scopes=dict(grouped),
            unrestricted_modules=self.unrestricted_modules(user),
        )

    def active_user_scopes(self, actor: User, *, scope_type: str | None = None, module: str | None = None) -> list[UserScope]:
        now = datetime.now(UTC)
        stmt = select(UserScope).where(
            UserScope.user_id == actor.id,
            UserScope.is_active.is_(True),
            UserScope.status == "active",
            or_(UserScope.starts_at.is_(None), UserScope.starts_at <= now),
            or_(UserScope.ends_at.is_(None), UserScope.ends_at >= now),
        )
        if actor.branch_id:
            stmt = stmt.where(or_(UserScope.branch_id == actor.branch_id, UserScope.branch_id.is_(None)))
        if scope_type:
            stmt = stmt.where(UserScope.scope_type == scope_type)
        if module:
            stmt = stmt.where(or_(UserScope.module == module, UserScope.module.is_(None)))
        return list(self.db.scalars(stmt))

    def active_role_scopes(self, actor: User, *, scope_type: str | None = None, module: str | None = None) -> list[RoleScope]:
        now = datetime.now(UTC)
        role_ids = [role.id for role in actor.roles if role.is_active]
        if not role_ids:
            return []
        stmt = select(RoleScope).where(
            RoleScope.role_id.in_(role_ids),
            RoleScope.is_active.is_(True),
            RoleScope.status == "active",
            or_(RoleScope.starts_at.is_(None), RoleScope.starts_at <= now),
            or_(RoleScope.ends_at.is_(None), RoleScope.ends_at >= now),
        )
        if actor.branch_id:
            stmt = stmt.where(or_(RoleScope.branch_id == actor.branch_id, RoleScope.branch_id.is_(None)))
        if scope_type:
            stmt = stmt.where(RoleScope.scope_type == scope_type)
        if module:
            stmt = stmt.where(or_(RoleScope.module == module, RoleScope.module.is_(None)))
        return list(self.db.scalars(stmt))

    def scope_values(self, actor: User, scope_type: str, *, module: str | None = None) -> set[str]:
        scopes = [*self.active_user_scopes(actor, scope_type=scope_type, module=module), *self.active_role_scopes(actor, scope_type=scope_type, module=module)]
        return {scope.scope_value.strip().lower() for scope in scopes if scope.scope_value}

    def scope_refs(self, actor: User, scope_type: str, *, module: str | None = None) -> set[UUID]:
        scopes = [*self.active_user_scopes(actor, scope_type=scope_type, module=module), *self.active_role_scopes(actor, scope_type=scope_type, module=module)]
        return {scope.scope_ref_id for scope in scopes if scope.scope_ref_id}

    def has_scope_assignments(self, actor: User, *scope_types: str, module: str | None = None) -> bool:
        return any(self.scope_values(actor, scope_type, module=module) or self.scope_refs(actor, scope_type, module=module) for scope_type in scope_types)

    def has_unrestricted_access(self, actor: User, *, module: str | None = None, scope_type: str | None = None) -> bool:
        permissions = set(self.auth.get_effective_permissions(actor))
        if permissions.intersection({SCOPE_OVERRIDE_PERMISSION, SCOPE_MANAGE_PERMISSION, "admin.manage_users"}):
            return True
        if scope_type and any(permission in permissions for permission in SUPERVISOR_PERMISSIONS.get(scope_type, ())):
            return True
        if module and f"{module}.scope.all" in permissions:
            return True
        hospital_values = self.scope_values(actor, "hospital", module=module)
        return "all" in hospital_values or "*" in hospital_values

    def unrestricted_modules(self, actor: User) -> list[str]:
        permissions = set(self.auth.get_effective_permissions(actor))
        modules = []
        for permission in permissions:
            if permission.endswith(".scope.all"):
                modules.append(permission.removesuffix(".scope.all"))
        if permissions.intersection({SCOPE_OVERRIDE_PERMISSION, SCOPE_MANAGE_PERMISSION, "admin.manage_users"}):
            modules.append("*")
        return sorted(set(modules))

    def assert_in_scope(
        self,
        actor: User,
        *,
        module: str,
        scope_type: str,
        scope_value: str | None = None,
        scope_ref_id: UUID | None = None,
        context: dict[str, str | None] | None = None,
    ) -> None:
        if self.has_unrestricted_access(actor, module=module, scope_type=scope_type):
            return
        if not self.has_scope_assignments(actor, scope_type, module=module):
            return
        values = self.scope_values(actor, scope_type, module=module)
        refs = self.scope_refs(actor, scope_type, module=module)
        value_ok = bool(scope_value and scope_value.strip().lower() in values)
        ref_ok = bool(scope_ref_id and scope_ref_id in refs)
        if value_ok or ref_ok:
            return
        self._audit(actor, "scope.access.denied", module, None, {"scope_type": scope_type, "scope_value": scope_value, "scope_ref_id": str(scope_ref_id) if scope_ref_id else None}, context or {})
        raise AppException(403, "scope_forbidden", "This record is outside your assigned operational scope")

    def filter_by_string_scope(self, stmt, actor: User, column, scope_type: str, *, module: str | None = None):
        if self.has_unrestricted_access(actor, module=module, scope_type=scope_type):
            return stmt
        values = self.scope_values(actor, scope_type, module=module)
        if not values:
            return stmt
        return stmt.where(func.lower(column).in_(values))

    def filter_by_ref_scope(self, stmt, actor: User, column, scope_type: str, *, module: str | None = None):
        if self.has_unrestricted_access(actor, module=module, scope_type=scope_type):
            return stmt
        refs = self.scope_refs(actor, scope_type, module=module)
        if not refs:
            return stmt
        return stmt.where(column.in_(refs))

    def _scope_payload(self, scope: UserScope | RoleScope) -> dict[str, Any]:
        return {
            "scope_type": scope.scope_type,
            "scope_value": scope.scope_value,
            "scope_ref_id": str(scope.scope_ref_id) if scope.scope_ref_id else None,
            "module": scope.module,
            "is_primary": scope.is_primary,
            "starts_at": scope.starts_at.isoformat() if scope.starts_at else None,
            "ends_at": scope.ends_at.isoformat() if scope.ends_at else None,
        }

    def _audit(self, actor: User, action: str, entity_type: str | None, entity_id: UUID | None, detail: dict | None, context: dict[str, str | None]) -> None:
        AuditService(self.db).log(
            user_id=actor.id,
            action=action,
            module="access_scope",
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            detail=detail or {},
            context=context,
        )
