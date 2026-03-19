from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.permission import Permission
from app.models.role import Role


class RolesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_roles(self) -> list[Role]:
        stmt = select(Role).options(joinedload(Role.permissions)).order_by(Role.name.asc())
        return list(self.db.scalars(stmt).unique())

    def get_role_by_code(self, code: str) -> Role | None:
        stmt = select(Role).options(joinedload(Role.permissions)).where(Role.code == code)
        return self.db.scalar(stmt)

    def get_permissions(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(codes))
        return list(self.db.scalars(stmt))

    def create_role(self, role: Role) -> Role:
        self.db.add(role)
        self.db.flush()
        return role

