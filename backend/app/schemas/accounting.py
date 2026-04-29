from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AccountingJournalCreate(BaseModel):
    branch_id: UUID | None = None
    reference: str | None = None
    description: str = Field(min_length=3)
    debit_amount: Decimal
    credit_amount: Decimal

    @model_validator(mode="after")
    def validate_balanced(self) -> "AccountingJournalCreate":
        if self.debit_amount != self.credit_amount:
            raise ValueError("Debit and credit amounts must match")
        return self


class AccountingJournalRead(BaseModel):
    id: UUID
    journal_number: str
    description: str
    debit_amount: Decimal
    credit_amount: Decimal
    status: str

    model_config = {"from_attributes": True}


class AccountingKPI(BaseModel):
    label: str
    value: Decimal | int
    tone: str = "info"
    description: str | None = None


class AccountingChartPoint(BaseModel):
    label: str
    value: Decimal | int


class AccountingAlert(BaseModel):
    severity: str
    title: str
    message: str


class AccountingDashboardRead(BaseModel):
    kpis: list[AccountingKPI]
    revenue_vs_expense: list[AccountingChartPoint]
    department_revenue: list[AccountingChartPoint]
    payment_methods: list[AccountingChartPoint]
    expense_breakdown: list[AccountingChartPoint]
    due_aging: list[AccountingChartPoint]
    payable_aging: list[AccountingChartPoint]
    cash_flow: list[AccountingChartPoint]
    alerts: list[AccountingAlert]


class AccountCreate(BaseModel):
    group_id: UUID | None = None
    account_code: str = Field(max_length=50)
    name: str = Field(max_length=160)
    category: str = Field(max_length=40)
    normal_balance: str = Field(default="debit", max_length=20)
    module_key: str | None = Field(default=None, max_length=80)
    mapped_entity: str | None = Field(default=None, max_length=120)
    opening_balance: Decimal = 0
    current_balance: Decimal = 0
    description: str | None = None
    is_active: bool = True


class AccountRead(AccountCreate):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class JournalEntryLineCreate(BaseModel):
    account_id: UUID | None = None
    account_code: str = Field(max_length=50)
    account_name: str = Field(max_length=160)
    description: str | None = None
    debit_amount: Decimal = 0
    credit_amount: Decimal = 0
    cost_center: str | None = None


class JournalEntryCreate(BaseModel):
    journal_date: date
    source_module: str | None = None
    source_reference: str | None = None
    narration: str = Field(min_length=3)
    status: str = "posted"
    attachment_url: str | None = None
    lines: list[JournalEntryLineCreate] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_balanced_lines(self) -> "JournalEntryCreate":
        debit = sum(line.debit_amount for line in self.lines)
        credit = sum(line.credit_amount for line in self.lines)
        if debit <= 0 or debit != credit:
            raise ValueError("Journal entry must have equal debit and credit totals")
        return self


class JournalEntryLineRead(JournalEntryLineCreate):
    id: UUID

    model_config = {"from_attributes": True}


class JournalEntryRead(BaseModel):
    id: UUID
    journal_number: str
    journal_date: date
    source_module: str | None
    source_reference: str | None
    narration: str
    status: str
    total_debit: Decimal
    total_credit: Decimal
    lines: list[JournalEntryLineRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class SimpleFinanceCreate(BaseModel):
    reference: str | None = None
    name: str | None = None
    amount: Decimal
    category: str | None = None
    status: str = "pending"
    payment_method: str = "cash"
    note: str | None = None


class FinanceRecordRead(BaseModel):
    id: UUID
    reference: str
    name: str
    amount: Decimal
    paid_amount: Decimal = 0
    due_amount: Decimal = 0
    category: str | None = None
    status: str
    created_at: datetime


class AccountingWorkspaceRead(BaseModel):
    accounts: list[AccountRead]
    journal_entries: list[JournalEntryRead]
    advances: list[FinanceRecordRead]
    discounts: list[FinanceRecordRead]
    refunds: list[FinanceRecordRead]
    insurance_claims: list[FinanceRecordRead]
    corporate_bills: list[FinanceRecordRead]
    supplier_invoices: list[FinanceRecordRead]
    expenses: list[FinanceRecordRead]
    doctor_commissions: list[FinanceRecordRead]
    cash_closings: list[FinanceRecordRead]
    bank_transactions: list[FinanceRecordRead]
