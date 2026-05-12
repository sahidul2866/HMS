from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StaffBotContext(BaseModel):
    module: str | None = None
    page: str | None = None
    path: str | None = None
    record_type: str | None = None
    record_id: str | None = None
    selected_label: str | None = None
    patient_id: str | None = None
    employee_id: str | None = None
    invoice_id: str | None = None
    visit_id: str | None = None
    appointment_id: str | None = None
    order_id: str | None = None
    filters: dict[str, Any] = {}


class StaffBotMessageCreate(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None
    context: StaffBotContext | str | None = None


class StaffBotResetCreate(BaseModel):
    context: StaffBotContext | str | None = None


class StaffBotDetailRow(BaseModel):
    label: str
    value: str


class StaffBotResponse(BaseModel):
    conversation_id: UUID
    message: str
    intent: str = "unknown"
    source_module: str = "unknown"
    used_database: bool = False
    used_gemini: bool = False
    details: list[StaffBotDetailRow] = []
    next_action: str | None = None
    quick_replies: list[str] = []
    follow_up: bool = False
    required_fields: list[str] = []
    permission_denied: bool = False
    context_suggestions: list[str] = []
    context_summary: str | None = None
    draft_content: str | None = None
    disclaimer: str | None = None
    actions: list[dict[str, Any]] = []
    requires_confirmation: bool = False
    confirmation_token: str | None = None


class StaffBotSettingsRead(BaseModel):
    greeting_message: str
    quick_actions: list[str]
    gemini_enabled: bool
    enabled: bool = True
    module_availability: dict[str, bool] = {}
    role_rules: dict[str, Any] = {}
    action_rules: dict[str, Any] = {}
    audit_logging: bool = True
    context: str | None = None


class StaffBotSettingUpsert(BaseModel):
    setting_key: str = Field(min_length=2, max_length=120)
    setting_value: dict[str, Any]


class StaffBotSettingRead(BaseModel):
    id: UUID
    setting_key: str
    setting_value: dict[str, Any]

    class Config:
        from_attributes = True


IntentKey = Literal[
    "patient_info",
    "opd_today_summary",
    "ipd_bed_occupancy",
    "pharmacy_stock",
    "billing_due",
    "pending_payments",
    "doctor_guidance",
    "appointment_status",
    "opd_booking",
    "hospital_summary",
    "revenue_analysis",
    "prescription_info",
    "permission_check",
    "general_health_guidance",
    "unknown",
]
