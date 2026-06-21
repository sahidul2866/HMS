from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.user import CurrentUserRead


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class LoginResponse(BaseModel):
    user: CurrentUserRead
    tokens: TokenPair


class PatientPortalAccountRead(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    branch_id: str | None = None
    department_id: None = None
    patient_id: str
    is_active: bool
    opd_consultation_fee: str = "0.00"
    opd_follow_up_fee: str = "0.00"
    opd_follow_up_days: int = 30
    opd_prescription_header_name: None = None
    opd_prescription_header_degrees: None = None
    opd_prescription_header_specialty: None = None
    opd_prescription_header_workplace: None = None
    opd_prescription_header_chamber: None = None
    opd_prescription_header_phone: None = None
    opd_prescription_header_address: None = None
    last_login_at: datetime | None = None
    roles: list = []
    direct_permissions: list = []
    effective_permissions: list[str] = ["patient.portal.view"]
    principal_type: str = "patient"


class PatientLoginResponse(BaseModel):
    user: PatientPortalAccountRead
    tokens: TokenPair


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class PasswordResetRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PatientRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    phone: str = Field(min_length=5, max_length=30)
    gender: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class PatientPortalAccountCreate(BaseModel):
    patient_id: str
    username: str = Field(min_length=3, max_length=80)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
