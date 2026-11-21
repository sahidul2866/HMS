from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.permission import PermissionRead
from app.schemas.role import RoleRead


class SignatureValidation(BaseModel):
    @field_validator('opd_signature_image',check_fields=False)
    @classmethod
    def validate_signature_image(cls,value):
        if value is None:return value
        import base64
        try:raw=base64.b64decode(value.split(',',1)[1],validate=True)
        except Exception:raise ValueError('Signature must be a valid PNG/JPEG data image')
        if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):raise ValueError('Signature must contain PNG or JPEG image bytes')
        return value


class UserCreate(SignatureValidation):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    employee_id: UUID | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    patient_id: UUID | None = None
    role_codes: list[str] = []
    direct_permission_codes: list[str] = []
    is_active: bool = True
    opd_consultation_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_days: int = Field(default=30, ge=1)
    opd_bmdc_registration: str | None = Field(default=None, max_length=80)
    opd_signature_image: str | None = Field(default=None, max_length=500000, pattern=r'^data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+$')
    opd_prescription_header_name: str | None = Field(default=None, max_length=180)
    opd_prescription_header_degrees: str | None = Field(default=None, max_length=300)
    opd_prescription_header_specialty: str | None = Field(default=None, max_length=220)
    opd_prescription_header_workplace: str | None = Field(default=None, max_length=220)
    opd_prescription_header_chamber: str | None = Field(default=None, max_length=220)
    opd_prescription_header_phone: str | None = Field(default=None, max_length=80)
    opd_prescription_header_address: str | None = Field(default=None, max_length=300)


class UserOPDSettingsUpdate(SignatureValidation):
    opd_consultation_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_fee: Decimal = Field(default=0, ge=0)
    opd_follow_up_days: int = Field(default=30, ge=1)
    opd_bmdc_registration: str | None = Field(default=None, max_length=80)
    opd_signature_image: str | None = Field(default=None, max_length=500000, pattern=r'^data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+$')
    opd_prescription_header_name: str | None = Field(default=None, max_length=180)
    opd_prescription_header_degrees: str | None = Field(default=None, max_length=300)
    opd_prescription_header_specialty: str | None = Field(default=None, max_length=220)
    opd_prescription_header_workplace: str | None = Field(default=None, max_length=220)
    opd_prescription_header_chamber: str | None = Field(default=None, max_length=220)
    opd_prescription_header_phone: str | None = Field(default=None, max_length=80)
    opd_prescription_header_address: str | None = Field(default=None, max_length=300)


class UserRead(SignatureValidation):
    id: UUID
    username: str
    email: str
    full_name: str
    must_reset_password: bool = False
    employee_id: UUID | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    patient_id: UUID | None = None
    is_active: bool
    opd_consultation_fee: Decimal = 0
    opd_follow_up_fee: Decimal = 0
    opd_follow_up_days: int = 30
    opd_bmdc_registration: str | None = Field(default=None, max_length=80)
    opd_signature_image: str | None = Field(default=None, max_length=500000, pattern=r'^data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+$')
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
