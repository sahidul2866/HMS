from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class BillingService(Base, BaseModelMixin):
    __tablename__ = "billing_services"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    service_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    doctor_share_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    branch = relationship("Branch")
    invoice_items = relationship("BillingInvoiceItem", back_populates="billing_service")


class ReferredDoctor(Base, BaseModelMixin):
    __tablename__ = "referred_doctors"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    doctor_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))

    branch = relationship("Branch")
    invoices = relationship("BillingInvoice", back_populates="referred_doctor")


class BillingInvoice(Base, BaseModelMixin):
    __tablename__ = "billing_invoices"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    internal_referral_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    referred_doctor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("referred_doctors.id"))
    referred_doctor_name: Mapped[str | None] = mapped_column(String(150))
    sub_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    referred_doctor_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="posted")
    void_reason: Mapped[str | None] = mapped_column(Text)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)
    billed_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    patient = relationship("Patient")
    internal_referral_user = relationship("User", foreign_keys=[internal_referral_user_id])
    referred_doctor = relationship("ReferredDoctor", back_populates="invoices")
    billed_by = relationship("User", foreign_keys=[billed_by_user_id], back_populates="billed_invoices")
    voided_by = relationship("User", foreign_keys=[voided_by_user_id], back_populates="voided_invoices")
    items = relationship("BillingInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class BillingInvoiceItem(Base, BaseModelMixin):
    __tablename__ = "billing_invoice_items"

    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=False)
    billing_service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_services.id"), nullable=False)
    service_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    doctor_share_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    doctor_share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    invoice = relationship("BillingInvoice", back_populates="items")
    billing_service = relationship("BillingService", back_populates="invoice_items")
