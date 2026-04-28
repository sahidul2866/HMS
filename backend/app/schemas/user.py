from datetime import datetime
from decimal import Decimal
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
    patient_id: UUID | None = None
    role_codes: list[str] = []
    direct_permission_codes: list[str] = []
    is_active: bool = True
    opd_consultation_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_days: int = Field(default=30, ge=1)
    opd_prescription_header_name: str | None = Field(default=None, max_length=180)
    opd_prescription_header_degrees: str | None = Field(default=None, max_length=300)
    opd_prescription_header_specialty: str | None = Field(default=None, max_length=220)
    opd_prescription_header_workplace: str | None = Field(default=None, max_length=220)
    opd_prescription_header_chamber: str | None = Field(default=None, max_length=220)
    opd_prescription_header_phone: str | None = Field(default=None, max_length=80)
    opd_prescription_header_address: str | None = Field(default=None, max_length=300)


class UserOPDSettingsUpdate(BaseModel):
    opd_consultation_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_days: int = Field(default=30, ge=1)
    opd_prescription_header_name: str | None = Field(default=None, max_length=180)
    opd_prescription_header_degrees: str | None = Field(default=None, max_length=300)
    opd_prescription_header_specialty: str | None = Field(default=None, max_length=220)
    opd_prescription_header_workplace: str | None = Field(default=None, max_length=220)
    opd_prescription_header_chamber: str | None = Field(default=None, max_length=220)
    opd_prescription_header_phone: str | None = Field(default=None, max_length=80)
    opd_prescription_header_address: str | None = Field(default=None, max_length=300)


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    branch_id: UUID | None = None
    department_id: UUID | None = None
    patient_id: UUID | None = None
    is_active: bool
    opd_consultation_fee: Decimal = 0
    opd_follow_up_fee: Decimal = 0
    opd_follow_up_days: int = 30
    opd_prescription_header_name: str | None = None
    opd_prescription_header_degrees: str | None = None
    opd_prescription_header_specialty: str | None = None
    opd_prescription_header_workplace: str | None = None
    opd_prescription_header_chamber: str | None = None
    opd_prescription_header_phone: str | None = None
    opd_prescription_header_address: str | None = None
    last_login_at: datetime | None = None
    roles: list[RoleRead] = []
    direct_permissions: list[PermissionRead] = []

    model_config = {"from_attributes": True}


class CurrentUserRead(UserRead):
    effective_permissions: list[str]
