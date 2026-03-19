from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.branches.service import BranchesService
from app.schemas.branch import BranchCreate, BranchRead

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("", response_model=list[BranchRead], dependencies=[Depends(require_permissions("settings.branch.manage"))])
def list_branches(db: Session = Depends(get_db)) -> list[BranchRead]:
    return [BranchRead.model_validate(item, from_attributes=True) for item in BranchesService(db).list_branches()]


@router.post("", response_model=BranchRead, dependencies=[Depends(require_permissions("settings.branch.manage"))])
def create_branch(payload: BranchCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> BranchRead:
    branch = BranchesService(db).create_branch(payload, user.id)
    return BranchRead.model_validate(branch, from_attributes=True)

