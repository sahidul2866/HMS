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

    def get_user(self, user_id) -> User | None:
        stmt = select(User).options(joinedload(User.roles), joinedload(User.direct_permissions)).where(User.id == user_id)
        return self.db.scalar(stmt)

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

    def list_doctors(self, *, referral_only: bool = False) -> list[User]:
        stmt = (
            select(User)
            .join(User.roles)
            .options(joinedload(User.roles), joinedload(User.direct_permissions))
            .where(User.is_active.is_(True), Role.is_doctor_role.is_(True))
            .order_by(User.full_name.asc())
        )
        if referral_only:
            stmt = stmt.where(Role.is_referral_role.is_(True))
        return list(self.db.scalars(stmt).unique())
