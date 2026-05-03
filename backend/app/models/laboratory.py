from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class LabOrder(Base, BaseModelMixin):
    __tablename__ = "lab_orders"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    er_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("er_visits.id"))
    order_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="routine")
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
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
    collected_by = relationship("User", foreign_keys=[collected_by_user_id])
    received_by = relationship("User", foreign_keys=[received_by_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    items = relationship("LabOrderItem", back_populates="order", cascade="all, delete-orphan")
    results = relationship("LabResult", back_populates="order", cascade="all, delete-orphan")
    attachments = relationship("LabAttachment", back_populates="order", cascade="all, delete-orphan")
    source_visit_orders = relationship("OPDVisitOrder", back_populates="lab_order")


class LabOrderItem(Base, BaseModelMixin):
    __tablename__ = "lab_order_items"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False)
    test_name: Mapped[str] = mapped_column(String(180), nullable=False)
    specimen_type: Mapped[str | None] = mapped_column(String(60))
    specimen_instructions: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reference_range_low: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    reference_range_high: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    reference_range_text: Mapped[str | None] = mapped_column(String(180))
    unit: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ordered")
    note: Mapped[str | None] = mapped_column(Text)

    order = relationship("LabOrder", back_populates="items")
    result_items = relationship("LabResultItem", back_populates="order_item")


class LabResult(Base, BaseModelMixin):
    __tablename__ = "lab_results"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False)
    report_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="preliminary")
    overall_interpretation: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)

    order = relationship("LabOrder", back_populates="results")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    items = relationship("LabResultItem", back_populates="result", cascade="all, delete-orphan")


class LabResultItem(Base, BaseModelMixin):
    __tablename__ = "lab_result_items"

    result_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_results.id"), nullable=False)
    order_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_order_items.id"))
    analyte_name: Mapped[str] = mapped_column(String(150), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(60))
    reference_range_low: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    reference_range_high: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    reference_range_text: Mapped[str | None] = mapped_column(String(180))
    flag: Mapped[str | None] = mapped_column(String(20))
    method: Mapped[str | None] = mapped_column(String(120))
    instrument: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)

    result = relationship("LabResult", back_populates="items")
    order_item = relationship("LabOrderItem", back_populates="result_items")


class LabAttachment(Base, BaseModelMixin):
    __tablename__ = "lab_attachments"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    order = relationship("LabOrder", back_populates="attachments")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
