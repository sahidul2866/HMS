from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class QueueCounter(Base, BaseModelMixin):
    __tablename__ = "queue_counters"
    __table_args__ = (UniqueConstraint("branch_id", "code", name="uq_queue_counters_branch_code"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    module: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    service_area: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    department_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    room_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    audio_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    display_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    current_token_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("queue_tokens.id"), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    doctor = relationship("User", foreign_keys=[doctor_user_id])
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    current_token = relationship("QueueToken", foreign_keys=[current_token_id], post_update=True)


class QueueToken(Base, BaseModelMixin):
    __tablename__ = "queue_tokens"
    __table_args__ = (
        UniqueConstraint("branch_id", "queue_scope", "token_date", "token_number", name="uq_queue_tokens_scope_number"),
        UniqueConstraint("queue_scope", "source_type", "source_id", name="uq_queue_tokens_scope_source"),
    )

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    token_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    token_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    token_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    queue_scope: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    service_area: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    department_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    counter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("queue_counters.id"), nullable=True, index=True)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True)
    patient_label: Mapped[str | None] = mapped_column(String(180), nullable=True)
    priority: Mapped[str] = mapped_column(String(30), nullable=False, default="normal", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="waiting", index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"), nullable=True, index=True)
    appointment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True, index=True)
    order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True, index=True)
    blood_request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("blood_requests.id"), nullable=True, index=True)
    called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    patient = relationship("Patient")
    doctor = relationship("User", foreign_keys=[doctor_user_id])
    counter = relationship("QueueCounter", foreign_keys=[counter_id])


class QueueAuditLog(Base, BaseModelMixin):
    __tablename__ = "queue_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    token_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("queue_tokens.id"), nullable=True, index=True)
    counter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("queue_counters.id"), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    module: Mapped[str | None] = mapped_column(String(60), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    token = relationship("QueueToken")
    counter = relationship("QueueCounter")
    user = relationship("User")


class QueueSetting(Base, BaseModelMixin):
    __tablename__ = "queue_settings"
    __table_args__ = (UniqueConstraint("branch_id", "setting_key", name="uq_queue_settings_branch_key"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    setting_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
