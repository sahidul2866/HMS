from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.users.service import UsersService
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/profile", response_model=UserRead)
def current_profile(user=Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)


@router.post("", response_model=UserRead, dependencies=[Depends(require_permissions("settings.user.manage"))])
def create_user(payload: UserCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    created = UsersService(db).create_user(payload, user.id, context)
    return UserRead.model_validate(created, from_attributes=True)
