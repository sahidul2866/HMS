from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class TaxRule(BaseModel):
    model_config={'extra':'forbid'}
    code: str=Field(pattern=r'^[A-Za-z0-9_-]{1,40}$')
    kind: Literal['output_vat','input_vat','withholding']
    rate: Decimal=Field(ge=0,le=100,decimal_places=4)
    exempt: bool=False
    inclusive: bool=False
    service_category: str=Field(min_length=1,max_length=100)
    effective_from: date
    effective_to: date | None=None
    ledger_account: str=Field(max_length=50)
    official_reference: str=Field(min_length=10,max_length=1000)
    review_note: str=Field(min_length=3,max_length=1000)


class AccountingSettings(BaseModel):
    model_config={'extra':'forbid'}
    currency: Literal['BDT']='BDT'
    timezone: Literal['Asia/Dhaka']='Asia/Dhaka'
    fiscal_start_month: int=Field(default=7,ge=1,le=12)
    recognition: Literal['accrual']='accrual'
    pharmacy_accounting_enabled: bool=True
    inventory_costing: Literal['weighted_average']='weighted_average'
    consultation_role: Literal['principal','agent']='principal'
    maker_checker: bool=True
    period_required: bool=True
    cutover_date: date
    legal_name: str=Field(max_length=180)
    registration_number: str=Field(default='',max_length=100)
    tin: str=Field(default='',max_length=100)
    bin: str=Field(default='',max_length=100)
    allow_negative_accounts: list[str]=Field(default_factory=list)
    cash_accounts: list[str]=Field(default_factory=lambda:['1001','1011','1012','1013','1020'])
    cash_flow_sources: dict[str,Literal['operating','investing','financing','unclassified']]=Field(default_factory=lambda:{'billing_payment':'operating','patient_advance':'operating','pharmacy_sale':'operating','billing_refund':'operating','supplier_payment':'operating','expense_payment':'operating','asset_disposal':'investing','hr_payroll':'operating','cash_transfer':'operating'})
    revenue_accounts: dict[str,str]=Field(default_factory=lambda:{'opd':'4010','ipd':'4020','laboratory':'4030','radiology':'4040','pharmacy':'4200','ot':'4060'})
    collection_accounts: dict[str,str]=Field(default_factory=lambda:{'cash':'1001','bank':'1020','bkash':'1031','nagad':'1032','rocket':'1033','card':'1034'})
    tax_rules: list[TaxRule]=Field(default_factory=list,max_length=100)
    payroll_attendance_treatment: Literal['reduce_expense','deduction_clearing']='reduce_expense'
    payroll_tax_account: str=Field(default='2250',max_length=50)
    payroll_payment_account: str=Field(default='1020',max_length=50)
    payroll_working_days: Decimal=Field(default=26,gt=0,le=366)
    payroll_late_day_fraction: Decimal=Field(default=Decimal('0.25'),ge=0,le=1)
    settlement_account: str=Field(default='1020',max_length=50)
    aging_days: list[int]=Field(default_factory=lambda:[0,30,60,90])
    expense_approval_limit: Decimal=Field(default=0,ge=0,decimal_places=2)

    @model_validator(mode='after')
    def validate_intervals(self):
        if not self.aging_days or self.aging_days[0]!=0 or self.aging_days!=sorted(set(self.aging_days)) or len(self.aging_days)>12:raise ValueError('Aging intervals must start at zero and be increasing')
        return self


class PolicyCreate(BaseModel):
    effective_from: date
    settings: AccountingSettings


class PeriodCreate(BaseModel):
    name: str=Field(min_length=3,max_length=100)
    start_date: date
    end_date: date
    @model_validator(mode='after')
    def valid_dates(self):
        if self.start_date>self.end_date:raise ValueError('Period end precedes start')
        return self


class AccountingReason(BaseModel):
    reason: str=Field(min_length=3,max_length=1000)


class AccountUpdate(BaseModel):
    name: str | None=Field(default=None,min_length=1,max_length=160)
    description: str | None=None
    parent_id: UUID | None=None
    reporting_group: str | None=Field(default=None,max_length=80)
    is_active: bool | None=None


class ShiftOpen(BaseModel):
    counter_name: str=Field(min_length=1,max_length=100)
    cash_account_code: str=Field(default='1001',max_length=50)
    opening_balance: Decimal=Field(ge=0,decimal_places=2)


class ShiftClose(BaseModel):
    counted_cash: Decimal=Field(ge=0,decimal_places=2)
    note: str=Field(default='',max_length=1000)


class CashTransfer(BaseModel):
    transaction_date: date
    from_account: str=Field(max_length=50)
    to_account: str=Field(max_length=50)
    amount: Decimal=Field(gt=0,decimal_places=2)
    processing_charge: Decimal=Field(default=0,ge=0,decimal_places=2)
    charge_account: str=Field(default='5160',max_length=50)
    reference: str=Field(min_length=3,max_length=100)
    request_key: str=Field(min_length=8,max_length=100)
    @model_validator(mode='after')
    def distinct(self):
        if self.from_account==self.to_account or self.processing_charge>=self.amount:raise ValueError('Choose distinct accounts and a charge smaller than the transfer')
        return self


class FinancePayment(BaseModel):
    amount: Decimal=Field(gt=0,decimal_places=2)
    payment_method: Literal['cash','bank_transfer','card','mobile_banking']='bank_transfer'
    payment_provider: str | None=Field(default=None,max_length=30)
    reference: str=Field(min_length=3,max_length=100)
    request_key: str=Field(min_length=8,max_length=64)


class TaxVoucher(BaseModel):
    transaction_date: date
    tax_code: str=Field(max_length=40)
    service_category: str=Field(max_length=100)
    basis_amount: Decimal=Field(gt=0,decimal_places=2)
    base_account: str=Field(max_length=50)
    counterpart_account: str=Field(max_length=50)
    document_reference: str=Field(min_length=3,max_length=100)
    request_key: str=Field(min_length=8,max_length=64)


class AssetCreate(BaseModel):
    asset_code: str=Field(min_length=1,max_length=80)
    name: str=Field(min_length=1,max_length=180)
    category: str=Field(min_length=1,max_length=100)
    department: str | None=Field(default=None,max_length=120)
    cost: Decimal=Field(gt=0,decimal_places=2)
    residual_value: Decimal=Field(default=0,ge=0,decimal_places=2)
    useful_life_months: int=Field(ge=1,le=1200)
    acquisition_date: date
    depreciation_start: date
    acquisition_journal_id: UUID
    @model_validator(mode='after')
    def valid_cost(self):
        if self.residual_value>self.cost or self.depreciation_start<self.acquisition_date:raise ValueError('Check asset residual value and depreciation start date')
        return self


class AssetDepreciation(BaseModel):
    month: str=Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')


class AssetDisposal(BaseModel):
    disposal_date: date
    proceeds: Decimal=Field(ge=0,decimal_places=2)
    receipt_account: str=Field(default='1020',max_length=50)
    reason: str=Field(min_length=3,max_length=1000)


class BankStatementRow(BaseModel):
    external_id: str=Field(min_length=1,max_length=120)
    transaction_date: date
    signed_amount: Decimal=Field(decimal_places=2)
    reference: str=Field(min_length=1,max_length=120)
    @model_validator(mode='after')
    def nonzero(self):
        if self.signed_amount==0:raise ValueError('Statement movement must be nonzero')
        return self


class BankStatementImport(BaseModel):
    ledger_account_code: str=Field(max_length=50)
    rows: list[BankStatementRow]=Field(min_length=1,max_length=500)


class BankStatementMatch(BaseModel):
    journal_id: UUID
    reason: str=Field(min_length=3,max_length=1000)


class PharmacyOpeningValue(BaseModel):
    journal_id: UUID
    amount: Decimal=Field(ge=0,decimal_places=2)
    reason: str=Field(min_length=3,max_length=1000)


class PaymentAdjustmentCreate(BaseModel):
    invoice_id: UUID
    payment_id: UUID | None=None
    kind: Literal['failed','chargeback','reversal']
    amount: Decimal=Field(gt=0,decimal_places=2,max_digits=14)
    deduction_account: str | None=Field(default=None,max_length=50)
    request_key: str=Field(min_length=8,max_length=100)
    reason: str=Field(min_length=3,max_length=1000)


class LegacyJournalResolution(BaseModel):
    journal_id: UUID
    treatment: Literal['already_posted','included_in_opening']
    reason: str=Field(min_length=10,max_length=2000)
