from sqlalchemy.orm import Session

from app.modules.admin.repository import AdminRepository
from app.modules.roles.service import RolesService
from app.modules.users.service import UsersService
from app.schemas.role import RoleCreate, RoleUpdatePermissions
from app.schemas.user import UserCreate, UserOPDSettingsUpdate


class AdminService:
    def __init__(self, db: Session) -> None:
        self.repository = AdminRepository(db)
        self.users = UsersService(db)
        self.roles = RolesService(db)

    def list_users(self):
        return self.users.list_users()

    def create_user(self, payload: UserCreate, actor_id, context):
        return self.users.create_user(payload, actor_id, context)

    def update_user_opd_settings(self, user_id, payload: UserOPDSettingsUpdate, actor_id, context):
        return self.users.update_opd_settings(user_id, payload, actor_id, context)

    def list_roles(self):
        return self.roles.list_roles()

    def create_role(self, payload: RoleCreate):
        return self.roles.create_role(payload)

    def update_role_permissions(self, code: str, payload: RoleUpdatePermissions, actor_id, context):
        return self.roles.update_role_permissions(code, payload, actor_id, context)
