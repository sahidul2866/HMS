from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class UserScope(Base, BaseModelMixin):
    __tablename__ = "user_scopes"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    scope_value: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    scope_ref_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    module: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_temporary: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_override: Mapped[bool] = mapped_column(default=False, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user = relationship("User")
    branch = relationship("Branch")


class RoleScope(Base, BaseModelMixin):
    __tablename__ = "role_scopes"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    role_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    scope_value: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    scope_ref_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    module: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    role = relationship("Role")
    branch = relationship("Branch")
