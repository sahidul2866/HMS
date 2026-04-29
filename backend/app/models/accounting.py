from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class AccountingJournal(Base, BaseModelMixin):
    __tablename__ = "accounting_journals"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    journal_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="posted", nullable=False)
    posted_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    posted_by = relationship("User")


class AccountGroup(Base, BaseModelMixin):
    __tablename__ = "account_groups"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("account_groups.id"))
    description: Mapped[str | None] = mapped_column(Text)

    parent = relationship("AccountGroup", remote_side="AccountGroup.id")


class Account(Base, BaseModelMixin):
    __tablename__ = "accounts"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    group_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("account_groups.id"))
    account_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(20), nullable=False, default="debit")
    module_key: Mapped[str | None] = mapped_column(String(80))
    mapped_entity: Mapped[str | None] = mapped_column(String(120))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)

    group = relationship("AccountGroup")


class JournalEntry(Base, BaseModelMixin):
    __tablename__ = "journal_entries"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    journal_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    journal_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_module: Mapped[str | None] = mapped_column(String(80))
    source_reference: Mapped[str | None] = mapped_column(String(120))
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    total_debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    reversed_entry_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("journal_entries.id"))
    attachment_url: Mapped[str | None] = mapped_column(String(500))

    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalEntryLine(Base, BaseModelMixin):
    __tablename__ = "journal_entry_lines"

    journal_entry_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id"))
    account_code: Mapped[str] = mapped_column(String(50), nullable=False)
    account_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    cost_center: Mapped[str | None] = mapped_column(String(120))

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account")


class PaymentMethod(Base, BaseModelMixin):
    __tablename__ = "payment_methods"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    method_type: Mapped[str] = mapped_column(String(40), nullable=False, default="cash")
    settlement_account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id"))
    requires_reference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AdvancePayment(Base, BaseModelMixin):
    __tablename__ = "advance_payments"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    receipt_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    source_module: Mapped[str | None] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    adjusted_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="cash")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    note: Mapped[str | None] = mapped_column(Text)
    collected_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class Discount(Base, BaseModelMixin):
    __tablename__ = "discounts"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    discount_type: Mapped[str] = mapped_column(String(40), nullable=False, default="fixed")
    discount_category: Mapped[str] = mapped_column(String(80), nullable=False, default="management")
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class Refund(Base, BaseModelMixin):
    __tablename__ = "refunds"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    refund_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    refund_type: Mapped[str] = mapped_column(String(80), nullable=False, default="service")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="cash")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    processed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class InsuranceClaim(Base, BaseModelMixin):
    __tablename__ = "insurance_claims"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    claim_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(160), nullable=False)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    rejected_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    patient_payable_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[date | None] = mapped_column(Date)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)


class CorporateBill(Base, BaseModelMixin):
    __tablename__ = "corporate_bills"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    company_name: Mapped[str] = mapped_column(String(180), nullable=False)
    bill_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    bill_month: Mapped[str] = mapped_column(String(7), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    due_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")


class SupplierInvoice(Base, BaseModelMixin):
    __tablename__ = "supplier_invoices"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    supplier_name: Mapped[str] = mapped_column(String(180), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="inventory")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    due_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    note: Mapped[str | None] = mapped_column(Text)


class SupplierPayment(Base, BaseModelMixin):
    __tablename__ = "supplier_payments"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    supplier_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("supplier_invoices.id"))
    payment_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="bank")
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="approved")
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class ExpenseCategory(Base, BaseModelMixin):
    __tablename__ = "expense_categories"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id"))
    monthly_budget: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)


class Expense(Base, BaseModelMixin):
    __tablename__ = "expenses"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    category_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("expense_categories.id"))
    expense_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(180))
    department_name: Mapped[str | None] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="cash")
    recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    description: Mapped[str | None] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class DoctorCommission(Base, BaseModelMixin):
    __tablename__ = "doctor_commissions"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    doctor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    doctor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_module: Mapped[str] = mapped_column(String(80), nullable=False, default="billing")
    reference_number: Mapped[str | None] = mapped_column(String(120))
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    commission_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="payable")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PayrollAccounting(Base, BaseModelMixin):
    __tablename__ = "payroll_accounting"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    payroll_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_payroll_runs.id"))
    payroll_month: Mapped[str] = mapped_column(String(7), nullable=False)
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    allowances: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_salary_payable: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="payable")


class CashClosing(Base, BaseModelMixin):
    __tablename__ = "cash_closing"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    cashier_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    closing_date: Mapped[date] = mapped_column(Date, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    cash_collection: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    refunds: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    cash_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    expected_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    actual_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    difference_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    remarks: Mapped[str | None] = mapped_column(Text)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class BankAccount(Base, BaseModelMixin):
    __tablename__ = "bank_accounts"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    account_name: Mapped[str] = mapped_column(String(160), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_number: Mapped[str] = mapped_column(String(80), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)


class BankTransaction(Base, BaseModelMixin):
    __tablename__ = "bank_transactions"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    bank_account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bank_accounts.id"))
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    matched_reference: Mapped[str | None] = mapped_column(String(120))
    reconciliation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="unmatched")
    note: Mapped[str | None] = mapped_column(Text)


class BankReconciliation(Base, BaseModelMixin):
    __tablename__ = "bank_reconciliations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    bank_account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bank_accounts.id"))
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    system_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bank_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    difference_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    reconciled_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class AccountingAuditLog(Base, BaseModelMixin):
    __tablename__ = "accounting_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(120))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(300))
