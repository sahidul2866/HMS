from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class Notification(Base, BaseModelMixin):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("recipient_user_id", "source_key", name="uq_notifications_recipient_source"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    recipient_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(24), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unread", index=True)
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False, default="instant", index=True)
    source_key: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    related_record_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    related_record_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    related_display: Mapped[str | None] = mapped_column(String(180), nullable=True)
    route: Mapped[str | None] = mapped_column(String(240), nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action_permission: Mapped[str | None] = mapped_column(String(120), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    recipient = relationship("User", foreign_keys=[recipient_user_id])


class NotificationAuditLog(Base, BaseModelMixin):
    __tablename__ = "notification_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    notification_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("notifications.id"), nullable=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    module: Mapped[str | None] = mapped_column(String(60), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    notification = relationship("Notification")
    user = relationship("User")


class NotificationSetting(Base, BaseModelMixin):
    __tablename__ = "notification_settings"
    __table_args__ = (UniqueConstraint("branch_id", "setting_key", name="uq_notification_settings_branch_key"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    setting_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
