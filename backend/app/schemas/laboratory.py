from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class LaboratorySummaryRead(BaseModel):
    total_orders: int
    pending_orders: int
    collected_orders: int
    in_progress_orders: int
    completed_orders: int
    verified_orders: int


class LabOrderItemRead(BaseModel):
    id: UUID
    test_name: str
    specimen_type: str | None = None
    specimen_instructions: str | None = None
    quantity: Decimal
    unit_price: Decimal | None = None
    reference_range_low: Decimal | None = None
    reference_range_high: Decimal | None = None
    reference_range_text: str | None = None
    unit: str | None = None
    status: str
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LabResultItemRead(BaseModel):
    id: UUID
    analyte_name: str
    value: str
    unit: str | None = None
    reference_range_low: Decimal | None = None
    reference_range_high: Decimal | None = None
    reference_range_text: str | None = None
    flag: str | None = None
    method: str | None = None
    instrument: str | None = None
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LabResultRead(BaseModel):
    id: UUID
    report_number: str
    status: str
    overall_interpretation: str | None = None
    items: list[LabResultItemRead] = []
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LabAttachmentRead(BaseModel):
    id: UUID
    file_name: str
    mime_type: str
    url: str
    file_size_bytes: int | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LabOrderRead(BaseModel):
    id: UUID
    order_number: str
    patient_id: UUID
    visit_id: UUID | None = None
    admission_id: UUID | None = None
    er_visit_id: UUID | None = None
    status: str
    priority: str
    collected_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    verified_at: datetime | None = None
    note: str | None = None
    items: list[LabOrderItemRead] = []
    results: list[LabResultRead] = []
    attachments: list[LabAttachmentRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}
