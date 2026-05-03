from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class RadiologyOrder(Base, BaseModelMixin):
    __tablename__ = "radiology_orders"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    er_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("er_visits.id"))
    order_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    modality: Mapped[str | None] = mapped_column(String(60))
    study_description: Mapped[str] = mapped_column(String(255), nullable=False)
    body_part: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="routine")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    patient = relationship("Patient")
    visit = relationship("OPDVisit")
    admission = relationship("IPDAdmission")
    er_visit = relationship("ERVisit")
    performed_by = relationship("User", foreign_keys=[performed_by_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    reports = relationship("RadiologyReport", back_populates="order", cascade="all, delete-orphan")
    attachments = relationship("RadiologyAttachment", back_populates="order", cascade="all, delete-orphan")
    pacs_links = relationship("PACSLink", back_populates="order", cascade="all, delete-orphan")
    source_visit_orders = relationship("OPDVisitOrder", back_populates="radiology_order")


class RadiologyReport(Base, BaseModelMixin):
    __tablename__ = "radiology_reports"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_orders.id"), nullable=False)
    report_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    overall_findings: Mapped[str | None] = mapped_column(Text)
    impression: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)

    order = relationship("RadiologyOrder", back_populates="reports")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    sections = relationship("RadiologyReportSection", back_populates="report", cascade="all, delete-orphan")


class RadiologyReportSection(Base, BaseModelMixin):
    __tablename__ = "radiology_report_sections"

    report_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_reports.id"), nullable=False)
    section_name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)

    report = relationship("RadiologyReport", back_populates="sections")


class RadiologyAttachment(Base, BaseModelMixin):
    __tablename__ = "radiology_attachments"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_orders.id"), nullable=False)
    report_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_reports.id"))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    order = relationship("RadiologyOrder", back_populates="attachments")
    report = relationship("RadiologyReport")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class PACSLink(Base, BaseModelMixin):
    __tablename__ = "pacs_links"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("radiology_orders.id"), nullable=False)
    study_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    series_uid: Mapped[str | None] = mapped_column(String(255))
    viewer_url: Mapped[str | None] = mapped_column(Text)
    pacs_provider: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="linked")

    order = relationship("RadiologyOrder", back_populates="pacs_links")
