from sqlalchemy.orm import Session

from app.modules.roles.repository import RolesRepository
from app.modules.users.repository import UsersRepository


class AdminRepository:
    def __init__(self, db: Session) -> None:
        self.users = UsersRepository(db)
        self.roles = RolesRepository(db)

