from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class PatientBotMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    selected_report_id: UUID | None = None
    selected_prescription_id: UUID | None = None


class PatientBotDoctorCard(BaseModel):
    id: UUID
    name: str
    department: str
    specialty: str
    qualification: str | None = None
    fee: str | None = None
    chamber: str | None = None
    available_today: bool = True
    languages: list[str] = Field(default_factory=lambda: ["Bangla", "English"])


class PatientBotResponse(BaseModel):
    conversation_id: UUID
    message: str
    type: str = "text"
    needs_more_input: bool = False
    recommended_department: str | None = None
    recommended_doctor_type: str | None = None
    safety_level: str = "normal"
    gemini_used: bool = False
    quick_replies: list[str] = Field(default_factory=list)
    doctor_cards: list[PatientBotDoctorCard] = Field(default_factory=list)
    context_summary: dict = Field(default_factory=dict)
    next_action: str | None = None


class PatientBotMessageRead(BaseModel):
    id: UUID
    sender: str
    message_type: str
    content: str
    payload: dict
    gemini_used: bool
    created_at: datetime


class PatientBotConversationRead(BaseModel):
    id: UUID
    title: str
    current_intent: str | None = None
    state: str
    intake: dict
    recommended_department: str | None = None
    recommended_doctor_type: str | None = None
    safety_level: str
    created_at: datetime
    updated_at: datetime
    messages: list[PatientBotMessageRead] = Field(default_factory=list)


class PatientBotSettingsRead(BaseModel):
    enabled: bool = True
    gemini_enabled: bool = False
    model_name: str
    max_gemini_calls_per_patient_per_day: int
    diet_guidance_enabled: bool = True
    report_explanation_enabled: bool = True
    prescription_explanation_enabled: bool = True
    appointment_booking_enabled: bool = True
    greeting_message: str
    quick_replies: list[str]


class PatientBotBookAppointmentRequest(BaseModel):
    conversation_id: UUID
    doctor_user_id: UUID
    appointment_at: datetime
    reason: str = Field(min_length=3, max_length=500)


class PatientBotDoctorsRead(BaseModel):
    department: str | None = None
    doctors: list[PatientBotDoctorCard]
    source_doctors: list[UserRead] = Field(default_factory=list)
