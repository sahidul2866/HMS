from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RadiologySummaryRead(BaseModel):
    total_orders: int
    pending_orders: int
    ready_orders: int
    in_progress_orders: int
    completed_orders: int
    verified_orders: int


class RadiologyReportSectionRead(BaseModel):
    id: UUID
    section_name: str
    content: str
    display_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RadiologyReportRead(BaseModel):
    id: UUID
    report_number: str
    status: str
    overall_findings: str | None = None
    impression: str | None = None
    recommendation: str | None = None
    sections: list[RadiologyReportSectionRead] = []
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RadiologyAttachmentRead(BaseModel):
    id: UUID
    file_name: str
    mime_type: str
    url: str
    file_size_bytes: int | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PACSLinkRead(BaseModel):
    id: UUID
    study_uid: str
    series_uid: str | None = None
    viewer_url: str | None = None
    pacs_provider: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RadiologyOrderRead(BaseModel):
    id: UUID
    order_number: str
    patient_id: UUID
    visit_id: UUID | None = None
    admission_id: UUID | None = None
    er_visit_id: UUID | None = None
    modality: str | None = None
    study_description: str
    body_part: str | None = None
    status: str
    priority: str
    scheduled_at: datetime | None = None
    performed_at: datetime | None = None
    completed_at: datetime | None = None
    verified_at: datetime | None = None
    note: str | None = None
    reports: list[RadiologyReportRead] = []
    attachments: list[RadiologyAttachmentRead] = []
    pacs_links: list[PACSLinkRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}
