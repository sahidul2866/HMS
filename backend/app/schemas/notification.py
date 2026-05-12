from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    id: UUID
    title: str
    message: str
    category: str
    module: str
    priority: str
    status: str
    notification_type: str
    related_record_type: str | None = None
    related_record_id: UUID | None = None
    related_display: str | None = None
    route: str | None = None
    action_label: str | None = None
    action_permission: str | None = None
    due_at: datetime | None = None
    read_at: datetime | None = None
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None
    escalated_at: datetime | None = None
    created_at: datetime
    meta: dict[str, Any] = {}
    action_allowed: bool = False
    overdue: bool = False

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int
    unread_count: int
    action_required_count: int
    critical_count: int


class NotificationSummary(BaseModel):
    unread_count: int
    action_required_count: int
    critical_count: int
    latest: list[NotificationRead]


class NotificationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(read|dismissed|completed|in_progress)$")


class NotificationSettingUpsert(BaseModel):
    setting_key: str = Field(min_length=2, max_length=120)
    setting_value: dict[str, Any]


class NotificationSettingRead(BaseModel):
    id: UUID
    setting_key: str
    setting_value: dict[str, Any]

    class Config:
        from_attributes = True
