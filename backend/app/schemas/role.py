from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.permission import PermissionRead


class RoleRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    is_doctor_role: bool = False
    is_referral_role: bool = False
    permissions: list[PermissionRead] = []

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=120)
    description: str | None = None
    is_doctor_role: bool = False
    is_referral_role: bool = False
    permission_codes: list[str] = []


class RoleUpdatePermissions(BaseModel):
    permission_codes: list[str]
