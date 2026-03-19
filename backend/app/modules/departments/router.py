from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.departments.service import DepartmentsService
from app.schemas.department import DepartmentCreate, DepartmentRead

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=list[DepartmentRead], dependencies=[Depends(require_permissions("settings.department.manage"))])
def list_departments(db: Session = Depends(get_db)) -> list[DepartmentRead]:
    return [DepartmentRead.model_validate(item, from_attributes=True) for item in DepartmentsService(db).list_departments()]


@router.post("", response_model=DepartmentRead, dependencies=[Depends(require_permissions("settings.department.manage"))])
def create_department(payload: DepartmentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> DepartmentRead:
    department = DepartmentsService(db).create_department(payload, user.id)
    return DepartmentRead.model_validate(department, from_attributes=True)

