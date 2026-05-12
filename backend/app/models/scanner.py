from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseModelMixin


class ScanCode(Base, BaseModelMixin):
    __tablename__ = "scan_codes"
    __table_args__ = (UniqueConstraint("code_value", name="uq_scan_codes_code_value"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    code_value: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    code_type: Mapped[str] = mapped_column(String(40), nullable=False, default="qr")
    purpose: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    record_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    display_value: Mapped[str | None] = mapped_column(String(180))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict | None] = mapped_column(JSON)


class ScanSetting(Base, BaseModelMixin):
    __tablename__ = "scan_settings"
    __table_args__ = (UniqueConstraint("branch_id", "department_id", "setting_key", name="uq_scan_settings_scope_key"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False)
    setting_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ScanEvent(Base, BaseModelMixin):
    __tablename__ = "scan_events"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    scanned_code: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    normalized_code: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    module: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str | None] = mapped_column(String(80))
    record_type: Mapped[str | None] = mapped_column(String(80))
    record_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    success: Mapped[str] = mapped_column(String(20), nullable=False, default="false")
    message: Mapped[str | None] = mapped_column(Text)
    device_label: Mapped[str | None] = mapped_column(String(160))
    location_label: Mapped[str | None] = mapped_column(String(160))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict | None] = mapped_column(JSON)

