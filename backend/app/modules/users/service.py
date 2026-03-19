from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import get_password_hash
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.users.repository import UsersRepository
from app.schemas.user import UserCreate
from app.utils.enums import AuditAction


class UsersService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UsersRepository(db)

    def list_users(self) -> list[User]:
        return self.repository.list_users()

    def create_user(self, payload: UserCreate, actor_id, context: dict[str, str | None]) -> User:
        existing = [user for user in self.repository.list_users() if user.username == payload.username or user.email == payload.email]
        if existing:
            raise AppException(409, "user_exists", "User with same username or email already exists")

        roles = self.repository.get_roles(payload.role_codes)
        permissions = self.repository.get_permissions(payload.direct_permission_codes)
        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            is_active=payload.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        user.roles = roles
        user.direct_permissions = permissions
        self.repository.create_user(user)
        AuditService(self.db).log(
            user_id=actor_id,
            action=AuditAction.USER_CREATE,
            module="admin",
            entity_type="user",
            entity_id=str(user.id),
            detail={"username": user.username, "roles": [role.code for role in roles]},
            context=context,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

