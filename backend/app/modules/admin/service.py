from sqlalchemy.orm import Session

from app.modules.admin.repository import AdminRepository
from app.modules.access_scope.service import AccessScopeService
from app.modules.roles.service import RolesService
from app.modules.users.service import UsersService
from app.schemas.role import RoleCreate, RoleUpdatePermissions
from app.schemas.scope import RoleScopeCreate, UserScopeCreate
from app.schemas.user import UserCreate, UserOPDSettingsUpdate


class AdminService:
    def __init__(self, db: Session) -> None:
        self.repository = AdminRepository(db)
        self.users = UsersService(db)
        self.roles = RolesService(db)
        self.scopes = AccessScopeService(db)

    def list_users(self):
        return self.users.list_users()

    def create_user(self, payload: UserCreate, actor_id, context):
        return self.users.create_user(payload, actor_id, context)

    def update_user_opd_settings(self, user_id, payload: UserOPDSettingsUpdate, actor_id, context):
        return self.users.update_opd_settings(user_id, payload, actor_id, context)

    def list_roles(self):
        return self.roles.list_roles()

    def create_role(self, payload: RoleCreate, actor_id, context):
        return self.roles.create_role(payload, actor_id, context)

    def update_role_permissions(self, code: str, payload: RoleUpdatePermissions, actor_id, context):
        return self.roles.update_role_permissions(code, payload, actor_id, context)

    def list_user_scopes(self, user_id=None):
        return self.scopes.list_user_scopes(user_id)

    def list_role_scopes(self, role_id=None):
        return self.scopes.list_role_scopes(role_id)

    def create_user_scope(self, payload: UserScopeCreate, actor, context):
        return self.scopes.create_user_scope(payload, actor, context)

    def create_role_scope(self, payload: RoleScopeCreate, actor, context):
        return self.scopes.create_role_scope(payload, actor, context)

    def deactivate_user_scope(self, scope_id, actor, context):
        return self.scopes.deactivate_user_scope(scope_id, actor, context)

    def deactivate_role_scope(self, scope_id, actor, context):
        return self.scopes.deactivate_role_scope(scope_id, actor, context)

    def effective_access(self, user_id):
        return self.scopes.effective_access(user_id)
