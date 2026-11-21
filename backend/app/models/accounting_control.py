"""Versioned branch accounting policies and exactly-once posting boundaries."""
from datetime import date
from uuid import UUID
from sqlalchemy import Date, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, BaseModelMixin


class AccountingPolicy(Base, BaseModelMixin):
    __tablename__ = 'accounting_policies'
    __table_args__ = (UniqueConstraint('branch_id','version',name='uq_accounting_policy_version'),)
    branch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),index=True)
    version: Mapped[int] = mapped_column(Integer,nullable=False)
    effective_from: Mapped[date] = mapped_column(Date,nullable=False)
    settings: Mapped[dict] = mapped_column(JSON,nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('users.id'))


class FinancialPeriod(Base, BaseModelMixin):
    __tablename__ = 'financial_periods'
    __table_args__ = (UniqueConstraint('branch_id','name',name='uq_financial_period_name'),)
    branch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),index=True)
    name: Mapped[str] = mapped_column(String(100),nullable=False)
    start_date: Mapped[date] = mapped_column(Date,nullable=False)
    end_date: Mapped[date] = mapped_column(Date,nullable=False)
    status: Mapped[str] = mapped_column(String(20),nullable=False,default='open')


class AccountingPostingKey(Base, BaseModelMixin):
    __tablename__ = 'accounting_posting_keys'
    __table_args__ = (UniqueConstraint('branch_id','source_module','source_reference',name='uq_accounting_posting_key'),)
    branch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'))
    source_module: Mapped[str] = mapped_column(String(80),nullable=False)
    source_reference: Mapped[str] = mapped_column(String(120),nullable=False)
    journal_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('journal_entries.id'))
    journal = relationship("JournalEntry")
    fingerprint: Mapped[str] = mapped_column(String(64),nullable=False)


from decimal import Decimal
from sqlalchemy import Numeric,Text


class FixedAsset(Base,BaseModelMixin):
    __tablename__='fixed_assets'
    __table_args__=(UniqueConstraint('branch_id','asset_code',name='uq_fixed_asset_code'),)
    branch_id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),index=True)
    asset_code: Mapped[str]=mapped_column(String(80),nullable=False)
    name: Mapped[str]=mapped_column(String(180),nullable=False)
    category: Mapped[str]=mapped_column(String(100),nullable=False)
    department: Mapped[str | None]=mapped_column(String(120))
    cost: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    residual_value: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    useful_life_months: Mapped[int]=mapped_column(Integer,nullable=False)
    acquisition_date: Mapped[date]=mapped_column(Date,nullable=False)
    depreciation_start: Mapped[date]=mapped_column(Date,nullable=False)
    depreciation_method: Mapped[str]=mapped_column(String(30),nullable=False,default='straight_line')
    accumulated_depreciation: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    last_depreciation_month: Mapped[str | None]=mapped_column(String(7))
    acquisition_journal_id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),ForeignKey('journal_entries.id'))
    status: Mapped[str]=mapped_column(String(20),nullable=False,default='active')


class AccountingPaymentAdjustment(Base,BaseModelMixin):
    __tablename__='accounting_payment_adjustments'
    __table_args__=(UniqueConstraint('branch_id','request_key',name='uq_accounting_payment_adjustment_request'),)
    branch_id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),index=True)
    invoice_id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),ForeignKey('billing_invoices.id'),index=True)
    payment_id: Mapped[UUID | None]=mapped_column(PGUUID(as_uuid=True),ForeignKey('billing_payments.id'))
    kind: Mapped[str]=mapped_column(String(30),nullable=False)
    amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    request_key: Mapped[str]=mapped_column(String(100),nullable=False)
    fingerprint: Mapped[str]=mapped_column(String(64),nullable=False)
    reason: Mapped[str]=mapped_column(Text,nullable=False)
    journal_id: Mapped[UUID | None]=mapped_column(PGUUID(as_uuid=True),ForeignKey('journal_entries.id'))
