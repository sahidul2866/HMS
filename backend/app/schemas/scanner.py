from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ScanResolveRequest(BaseModel):
    code: str = Field(min_length=1, max_length=220)
    module: str | None = None
    action: str | None = None
    expected_record_type: str | None = None
    expected_patient_id: UUID | None = None
    device_label: str | None = None
    location_label: str | None = None


class ScanResolvedRecord(BaseModel):
    record_type: str
    record_id: UUID
    display: str
    status: str | None = None
    route: str | None = None
    module: str
    permission: str
    safety: dict[str, Any] = {}
    data: dict[str, Any] = {}


class ScanResolveResponse(BaseModel):
    success: bool
    message: str
    code: str
    match_count: int = 0
    records: list[ScanResolvedRecord] = []
    action: str | None = None


class ScanCodeCreate(BaseModel):
    record_type: str
    record_id: UUID
    purpose: str
    code_type: str = "qr"
    display_value: str | None = None
    expires_at: datetime | None = None
    meta: dict[str, Any] | None = None


class ScanCodeRead(BaseModel):
    id: UUID
    code_value: str
    code_type: str
    purpose: str
    record_type: str
    record_id: UUID
    display_value: str | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScanSettingWrite(BaseModel):
    setting_key: str
    setting_value: dict[str, Any]
    department_id: UUID | None = None


class ScanSettingRead(ScanSettingWrite):
    id: UUID

    model_config = {"from_attributes": True}

