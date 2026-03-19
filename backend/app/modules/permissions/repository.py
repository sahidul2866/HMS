from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission


class PermissionsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.module.asc(), Permission.code.asc())
        return list(self.db.scalars(stmt))

