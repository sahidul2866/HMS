from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department


class DepartmentsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_departments(self) -> list[Department]:
        return list(self.db.scalars(select(Department).order_by(Department.name.asc())))

    def create_department(self, department: Department) -> Department:
        self.db.add(department)
        self.db.flush()
        return department

