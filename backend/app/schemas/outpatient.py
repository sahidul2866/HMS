from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class OutpatientDashboardRead(BaseModel):
    opd_waiting: int = 0
    telemedicine_waiting: int = 0
    called: int = 0
    in_consultation: int = 0
    completed_today: int = 0
    no_show: int = 0
    pending_payments: int = 0
    pending_prescriptions: int = 0
    by_visit_type: dict[str, int] = {}
    by_status: dict[str, int] = {}


class UnifiedOutpatientQueueItem(BaseModel):
    token_id: UUID | None = None
    source_id: UUID
    source_type: str
    visit_mode: str
    visit_type: str | None = None
    number: str
    queue_number: str | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    doctor_user_id: UUID | None = None
    doctor_name: str | None = None
    department_name: str | None = None
    appointment_at: datetime | None = None
    status: str
    queue_status: str | None = None
    payment_status: str | None = None
    waiting_minutes: int = 0
    priority: str = "normal"
    join_url: str | None = None
    current_complaint: str | None = None
    has_video_panel: bool = False
    meta: dict[str, Any] = {}


class OutpatientQueueAction(BaseModel):
    action: str
    notes: str | None = None


class OutpatientReportRead(BaseModel):
    report_type: str
    filters: dict[str, Any]
    rows: list[dict[str, Any]]
    totals: dict[str, Any]
