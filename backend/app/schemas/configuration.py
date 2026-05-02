from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConfigurationProfileBase(BaseModel):
    profile_type: str = Field(min_length=2, max_length=80)
    code: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=180)
    description: str | None = None
    scope: str = Field(default="hospital", max_length=60)
    target_type: str | None = Field(default=None, max_length=80)
    target_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_active: bool = True


class ConfigurationProfileCreate(ConfigurationProfileBase):
    pass


class ConfigurationProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str | None = None
    scope: str = Field(default="hospital", max_length=60)
    target_type: str | None = Field(default=None, max_length=80)
    target_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_active: bool = True


class ConfigurationProfileRead(ConfigurationProfileBase):
    id: UUID
    branch_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConfigurationWorkspaceRead(BaseModel):
    profiles: list[ConfigurationProfileRead]
    counts: dict[str, int]
    demo_points: list[str]
