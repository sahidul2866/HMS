from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


def _blank_to_none(data: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if data.get(key) in {"", "null", "undefined"}:
                data[key] = None
    return data


class TelemedicineDashboardRead(BaseModel):
    todays_online_appointments: int = 0
    waiting_patients: int = 0
    active_consultations: int = 0
    completed_consultations: int = 0
    missed_no_show: int = 0
    pending_payments: int = 0
    pending_prescriptions: int = 0
    follow_up_requests: int = 0
    doctors_available: int = 0
    by_status: dict[str, int] = {}
    by_payment_status: dict[str, int] = {}


class TelemedicineAppointmentCreate(BaseModel):
    patient_id: UUID
    department_id: UUID | None = None
    department_name: str | None = None
    doctor_user_id: UUID
    appointment_at: datetime
    consultation_reason: str | None = None
    visit_type: str = "new"
    appointment_type: str = "video"
    contact_phone: str | None = None
    contact_email: str | None = None
    uploaded_files: list[dict[str, Any]] = []
    payment_status: str = "pending"
    consultation_fee: Decimal = Decimal("0")
    consent_required: bool = True
    remarks: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        return _blank_to_none(data, ("department_id",))


class TelemedicineAppointmentRead(TelemedicineAppointmentCreate):
    id: UUID
    branch_id: UUID | None = None
    appointment_id: UUID | None = None
    telemedicine_number: str
    patient_name: str | None = None
    patient_number: str | None = None
    doctor_name: str | None = None
    queue_number: str | None = None
    estimated_wait_minutes: int | None = None
    status: str
    billing_invoice_id: UUID | None = None
    consent_accepted: bool
    consent_at: datetime | None = None
    consent_by: str | None = None
    consent_terms_version: str | None = None
    video_provider: str | None = None
    meeting_id: str | None = None
    join_url: str | None = None
    doctor_join_url: str | None = None
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class TelemedicineStatusUpdate(BaseModel):
    status: str
    remarks: str | None = None


class TelemedicineConsentUpdate(BaseModel):
    consent_accepted: bool = True
    consent_by: str
    consent_terms_version: str = "v1"


class TelemedicineConsultationUpdate(BaseModel):
    current_complaint: str | None = None
    notes: str | None = None
    diagnosis: str | None = None
    prescription_text: str | None = None
    advice: str | None = None
    follow_up_date: date | None = None
    follow_up_plan: str | None = None
    referral_department: str | None = None
    referral_doctor_user_id: UUID | None = None
    media_status: dict[str, Any] | None = None
    remarks: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        return _blank_to_none(data, ("follow_up_date", "referral_doctor_user_id"))


class TelemedicineConsultationRead(TelemedicineConsultationUpdate):
    id: UUID
    telemedicine_appointment_id: UUID
    telemedicine_number: str | None = None
    patient_id: UUID
    patient_name: str | None = None
    patient_number: str | None = None
    doctor_user_id: UUID
    doctor_name: str | None = None
    opd_visit_id: UUID | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    patient_joined_at: datetime | None = None
    doctor_joined_at: datetime | None = None
    connection_status: str
    status: str
    prescription_status: str
    completed_by_name: str | None = None
    completed_at: datetime | None = None
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class TelemedicineChatCreate(BaseModel):
    message: str = Field(min_length=1)
    message_type: str = "text"
    attachment_id: UUID | None = None


class TelemedicineChatRead(TelemedicineChatCreate):
    id: UUID
    consultation_id: UUID
    sender_user_id: UUID | None = None
    sender_patient_id: UUID | None = None
    sender_name: str | None = None
    sender_role: str
    read_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class TelemedicineFileCreate(BaseModel):
    telemedicine_appointment_id: UUID | None = None
    consultation_id: UUID | None = None
    patient_id: UUID
    file_category: str = "medical_document"
    file_name: str
    mime_type: str
    file_size_bytes: int = Field(ge=0)
    file_url: str
    remarks: str | None = None


class TelemedicineFileRead(TelemedicineFileCreate):
    id: UUID
    uploaded_by_name: str | None = None
    validation_status: str
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class TelemedicineInvestigationCreate(BaseModel):
    service_area: str = Field(pattern="^(laboratory|radiology)$")
    item_name: str = Field(min_length=2, max_length=180)
    instructions: str | None = None


class TelemedicineInvestigationRead(TelemedicineInvestigationCreate):
    id: UUID
    consultation_id: UUID
    patient_id: UUID
    lab_order_id: UUID | None = None
    radiology_order_id: UUID | None = None
    billing_status: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class TelemedicinePaymentUpdate(BaseModel):
    payment_status: str
    billing_invoice_id: UUID | None = None


class TelemedicineSettingCreate(BaseModel):
    setting_key: str = Field(min_length=2, max_length=120)
    setting_value: str
    description: str | None = None
    meta: dict[str, Any] | None = None


class TelemedicineSettingRead(TelemedicineSettingCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class TelemedicineReportRead(BaseModel):
    report_type: str
    filters: dict[str, Any]
    rows: list[dict[str, Any]]
    totals: dict[str, Any]
