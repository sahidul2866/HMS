from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


class UsersRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(self) -> list[User]:
        stmt = select(User).options(joinedload(User.roles), joinedload(User.direct_permissions)).order_by(User.created_at.desc())
        return list(self.db.scalars(stmt).unique())

    def get_roles(self, codes: list[str]) -> list[Role]:
        if not codes:
            return []
        stmt = select(Role).where(Role.code.in_(codes))
        return list(self.db.scalars(stmt))

    def get_permissions(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(codes))
        return list(self.db.scalars(stmt))

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

