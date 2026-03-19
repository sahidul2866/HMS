from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.modules.permissions.repository import PermissionsRepository


class PermissionsService:
    def __init__(self, db: Session) -> None:
        self.repository = PermissionsRepository(db)

    def list_permissions(self) -> list[Permission]:
        return self.repository.list_permissions()

