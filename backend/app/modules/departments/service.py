from sqlalchemy.orm import Session

from app.models.department import Department
from app.modules.departments.repository import DepartmentsRepository
from app.schemas.department import DepartmentCreate


class DepartmentsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DepartmentsRepository(db)

    def list_departments(self) -> list[Department]:
        return self.repository.list_departments()

    def create_department(self, payload: DepartmentCreate, actor_id) -> Department:
        department = Department(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        self.repository.create_department(department)
        self.db.commit()
        self.db.refresh(department)
        return department

