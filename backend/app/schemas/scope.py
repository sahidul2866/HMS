from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScopeAssignmentBase(BaseModel):
    scope_type: str = Field(min_length=2, max_length=60)
    scope_value: str | None = Field(default=None, max_length=180)
    scope_ref_id: UUID | None = None
    module: str | None = Field(default=None, max_length=60)
    status: str = Field(default="active", max_length=30)
    is_primary: bool = False
    is_temporary: bool = False
    is_override: bool = False
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str | None = None
    meta: dict = {}


class UserScopeCreate(ScopeAssignmentBase):
    user_id: UUID


class RoleScopeCreate(ScopeAssignmentBase):
    role_id: UUID


class UserScopeRead(ScopeAssignmentBase):
    id: UUID
    user_id: UUID
    branch_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleScopeRead(ScopeAssignmentBase):
    id: UUID
    role_id: UUID
    branch_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EffectiveAccessRead(BaseModel):
    user_id: UUID
    roles: list[dict]
    permissions: list[str]
    user_scopes: list[UserScopeRead]
    role_scopes: list[RoleScopeRead]
    effective_scopes: dict[str, list[dict]]
    unrestricted_modules: list[str]
