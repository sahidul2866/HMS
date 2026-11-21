from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, BaseModelMixin


class BillingPolicy(Base, BaseModelMixin):
    __tablename__ = 'billing_policies'
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey('branches.id'), index=True)
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    selector: Mapped[str] = mapped_column(String(150), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)


class BillingAllocation(Base, BaseModelMixin):
    """Append-only earnings/adjustments and settlement entries; negative balances are recoverable."""
    __tablename__ = 'billing_allocations'
    __table_args__ = (UniqueConstraint('branch_id', 'request_key', name='uq_billing_allocation_request'),)
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey('branches.id'), index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey('billing_invoices.id'), index=True)
    invoice_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey('billing_invoice_items.id'))
    participant_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    request_key: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class BillingCommand(Base, BaseModelMixin):
    __tablename__ = 'billing_commands'
    __table_args__ = (UniqueConstraint('invoice_id', 'request_key', name='uq_billing_command_request'),)
    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('billing_invoices.id'), nullable=False)
    request_key: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
