from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueueCounterCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=160)
    module: str = Field(min_length=2, max_length=60)
    service_area: str | None = None
    department_name: str | None = None
    room_number: str | None = None
    doctor_user_id: UUID | None = None
    assigned_user_id: UUID | None = None
    audio_enabled: bool = False
    display_enabled: bool = True
    settings: dict[str, Any] = {}


class QueueCounterRead(QueueCounterCreate):
    id: UUID
    status: str
    current_token_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class QueueTokenCreate(BaseModel):
    queue_scope: str = Field(min_length=2, max_length=60)
    module: str = Field(min_length=2, max_length=60)
    service_area: str | None = None
    department_name: str | None = None
    doctor_user_id: UUID | None = None
    counter_id: UUID | None = None
    patient_id: UUID | None = None
    patient_label: str | None = None
    priority: str = "normal"
    source_type: str = Field(min_length=2, max_length=80)
    source_id: UUID
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    order_id: UUID | None = None
    invoice_id: UUID | None = None
    blood_request_id: UUID | None = None
    due_at: datetime | None = None
    notes: str | None = None
    meta: dict[str, Any] = {}


class QueueTokenRead(BaseModel):
    id: UUID
    token_number: str
    token_sequence: int
    token_date: date
    queue_scope: str
    module: str
    service_area: str | None = None
    department_name: str | None = None
    doctor_user_id: UUID | None = None
    counter_id: UUID | None = None
    patient_id: UUID | None = None
    patient_label: str | None = None
    priority: str
    status: str
    source_type: str
    source_id: UUID
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    order_id: UUID | None = None
    invoice_id: UUID | None = None
    blood_request_id: UUID | None = None
    called_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    skipped_at: datetime | None = None
    recalled_at: datetime | None = None
    due_at: datetime | None = None
    notes: str | None = None
    meta: dict[str, Any] = {}
    created_at: datetime
    waiting_minutes: int = 0

    class Config:
        from_attributes = True


class QueueTokenStatusUpdate(BaseModel):
    status: str = Field(
        pattern=(
            "^(registered|waiting|called|in_progress|completed|skipped|recalled|cancelled|no_show|referred|"
            "sent_to_billing|sent_to_lab|sent_to_radiology|sent_to_pharmacy|sent_to_blood_bank|requested|"
            "sample_pending|sample_collected|crossmatch_pending|crossmatched|ready_to_issue|partially_issued|"
            "issued|returned|rejected|discarded)$"
        )
    )
    counter_id: UUID | None = None
    notes: str | None = None


class QueueTransferRequest(BaseModel):
    queue_scope: str
    module: str
    service_area: str | None = None
    department_name: str | None = None
    doctor_user_id: UUID | None = None
    counter_id: UUID | None = None
    priority: str | None = None
    notes: str | None = None


class QueueSummary(BaseModel):
    total_waiting: int
    total_called: int
    total_in_progress: int
    total_completed: int
    skipped_count: int
    longest_wait_minutes: int
    average_wait_minutes: int
    by_scope: dict[str, int]
    by_counter: dict[str, int]


class QueueDisplayRead(BaseModel):
    scope: str
    current: list[QueueTokenRead]
    next_tokens: list[QueueTokenRead]
    announcements: list[str] = []


class QueueSettingUpsert(BaseModel):
    setting_key: str = Field(min_length=2, max_length=120)
    setting_value: dict[str, Any]


class QueueSettingRead(BaseModel):
    id: UUID
    setting_key: str
    setting_value: dict[str, Any]

    class Config:
        from_attributes = True
