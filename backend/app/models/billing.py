from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
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
    max_discount_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    room_number: Mapped[str | None] = mapped_column(String(60))

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
    source_opd_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    source_ipd_admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    source_module: Mapped[str | None] = mapped_column(String(40))
    billing_stage: Mapped[str | None] = mapped_column(String(40))
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    internal_referral_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    referred_doctor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("referred_doctors.id"))
    referred_doctor_name: Mapped[str | None] = mapped_column(String(150))
    sub_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    item_discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    invoice_discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    due_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unpaid")
    referred_doctor_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="posted")
    void_reason: Mapped[str | None] = mapped_column(Text)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)
    billed_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    patient = relationship("Patient")
    source_opd_visit = relationship("OPDVisit", foreign_keys=[source_opd_visit_id])
    source_ipd_admission = relationship("IPDAdmission", foreign_keys=[source_ipd_admission_id])
    internal_referral_user = relationship("User", foreign_keys=[internal_referral_user_id])
    referred_doctor = relationship("ReferredDoctor", back_populates="invoices")
    billed_by = relationship("User", foreign_keys=[billed_by_user_id], back_populates="billed_invoices")
    voided_by = relationship("User", foreign_keys=[voided_by_user_id], back_populates="voided_invoices")
    items = relationship("BillingInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("BillingPayment", back_populates="invoice", cascade="all, delete-orphan")
    refunds = relationship("BillingRefund", back_populates="invoice", cascade="all, delete-orphan")


class BillingInvoiceItem(Base, BaseModelMixin):
    __tablename__ = "billing_invoice_items"

    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=False)
    billing_service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_services.id"), nullable=False)
    source_opd_visit_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visit_orders.id"))
    source_label: Mapped[str | None] = mapped_column(String(180))
    source_module: Mapped[str | None] = mapped_column(String(40))
    service_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_discount_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    room_number: Mapped[str | None] = mapped_column(String(60))
    doctor_share_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    doctor_share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    invoice = relationship("BillingInvoice", back_populates="items")
    billing_service = relationship("BillingService", back_populates="invoice_items")
    source_opd_visit_order = relationship("OPDVisitOrder", foreign_keys=[source_opd_visit_order_id])
    item_links = relationship("BillingItemLink", back_populates="invoice_item", cascade="all, delete-orphan")


class BillingPayment(Base, BaseModelMixin):
    __tablename__ = "billing_payments"

    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    receipt_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False, default="cash")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    invoice = relationship("BillingInvoice", back_populates="payments")
    patient = relationship("Patient")
    branch = relationship("Branch")
    collected_by = relationship("User", foreign_keys=[collected_by_user_id])
    refunds = relationship("BillingRefund", back_populates="payment")


class BillingRefund(Base, BaseModelMixin):
    __tablename__ = "billing_refunds"

    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=False)
    payment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_payments.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    refund_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    refunded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refunded_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    invoice = relationship("BillingInvoice", back_populates="refunds")
    payment = relationship("BillingPayment", back_populates="refunds")
    patient = relationship("Patient")
    branch = relationship("Branch")
    refunded_by = relationship("User", foreign_keys=[refunded_by_user_id])


class BillingSetting(Base, BaseModelMixin):
    __tablename__ = "billing_settings"
    __table_args__ = (UniqueConstraint("branch_id", name="uq_billing_settings_branch_id"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    max_item_discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    max_item_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    max_invoice_discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    max_invoice_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    default_referral_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    branch = relationship("Branch")
