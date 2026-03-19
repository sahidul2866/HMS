from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.permission import PermissionRead
from app.schemas.role import RoleRead


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    branch_id: UUID | None = None
    department_id: UUID | None = None
    role_codes: list[str] = []
    direct_permission_codes: list[str] = []
    is_active: bool = True


class UserRead(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    full_name: str
    branch_id: UUID | None = None
    department_id: UUID | None = None
    is_active: bool
    last_login_at: datetime | None = None
    roles: list[RoleRead] = []
    direct_permissions: list[PermissionRead] = []

    model_config = {"from_attributes": True}


class CurrentUserRead(UserRead):
    effective_permissions: list[str]

