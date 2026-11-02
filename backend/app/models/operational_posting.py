"""Append-only source links for automatic operational money/stock postings."""
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import Date, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, BaseModelMixin

class OperationalPosting(Base, BaseModelMixin):
    __tablename__ = 'operational_postings'
    __table_args__ = (UniqueConstraint('source_type','source_id','event',name='uq_operational_posting_source_event'),)
    branch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),nullable=False,index=True)
    source_type: Mapped[str] = mapped_column(String(60),nullable=False)
    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),nullable=False)
    event: Mapped[str] = mapped_column(String(60),nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2),nullable=False,default=0)
    invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('billing_invoices.id'))
    journal_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('journal_entries.id'))
    details: Mapped[dict | None] = mapped_column(JSON)

class HRSalaryRevision(Base, BaseModelMixin):
    __tablename__ = 'hr_salary_revisions'
    __table_args__ = (UniqueConstraint('employee_id','effective_from',name='uq_hr_salary_revision_date'),)
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('hr_employees.id'),nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),nullable=False)
    effective_from: Mapped[date] = mapped_column(Date,nullable=False)
    components: Mapped[dict] = mapped_column(JSON,nullable=False)

class HRPayrollAdjustment(Base, BaseModelMixin):
    __tablename__ = 'hr_payroll_adjustments'
    branch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'),nullable=False)
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('hr_employees.id'),nullable=False)
    source_payroll_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('hr_payroll_items.id'))
    payroll_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('hr_payroll_items.id'))
    target_month: Mapped[str] = mapped_column(String(7),nullable=False)
    kind: Mapped[str] = mapped_column(String(30),nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2),nullable=False)
    reason: Mapped[str] = mapped_column(Text,nullable=False)
    status: Mapped[str] = mapped_column(String(30),nullable=False,default='pending')
    employee = relationship('HREmployee', foreign_keys=[employee_id])
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('users.id'))

