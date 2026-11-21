"""Versioned financial policies. Decimal strings are preserved in JSON snapshots."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class Participant(BaseModel):
    key: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9:_-]+$')
    name: str = Field(min_length=1, max_length=150)
    kind: Literal['doctor', 'external_doctor', 'pharmacy', 'person', 'agent', 'organization', 'other']
    share: Decimal = Field(ge=0, le=100, decimal_places=4)


class FinancialRules(BaseModel):
    model_config = {"validate_default": True, "extra": "forbid"}
    default_discount_percentage: Decimal = Field(default=0, ge=0, le=100)
    hospital_name: str | None = Field(default=None, max_length=150)
    hospital_address: str | None = Field(default=None, max_length=500)
    hospital_contact: str | None = Field(default=None, max_length=150)
    discounts_allowed: bool = True
    max_percentage: Decimal = Field(default=100, ge=0, le=100)
    max_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    combine: bool = True
    approval_required: bool = False
    allowed_roles: list[str] = Field(default_factory=list)
    override_roles: list[str] = Field(default_factory=list)
    discount_sharing: dict[str, Decimal] = Field(default_factory=lambda: {'hospital': Decimal(100)})
    doctor_key: str | None = None
    doctor_revenue_percentage: Decimal = Field(default=0, ge=0, le=100)
    hospital_fixed_deduction: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    commission_enabled: bool = False
    commission_basis: Literal['gross', 'net'] = 'net'
    commission_percentage: Decimal = Field(default=0, ge=0, le=100)
    commission_fixed: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    commission_limit: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    commission_approval_required: bool = False
    participants: list[Participant] = Field(default_factory=list)
    refund_approval_required: bool = False
    consultation_cancellable: bool = True
    allow_started_cancellation: bool = False
    package_cancellation: Literal['quantity', 'whole'] = 'quantity'
    allow_advance_payments: bool = False
    show_item_discounts: bool = True

    @model_validator(mode='after')
    def shares_reconcile(self):
        if sum(self.discount_sharing.values()) != Decimal(100) or any(v < 0 or v > 100 for v in self.discount_sharing.values()):
            raise ValueError('Discount responsibility must total 100%')
        if self.default_discount_percentage > self.max_percentage:
            raise ValueError('Default discount exceeds the maximum percentage')
        keys = [p.key for p in self.participants]
        if len(keys) != len(set(keys)) or 'hospital' in keys:
            raise ValueError('Participant keys must be unique and separate from hospital')
        if (self.doctor_revenue_percentage or self.hospital_fixed_deduction is not None) and not self.doctor_key:
            raise ValueError('Doctor revenue requires a doctor account key')
        if self.commission_enabled and (not keys or sum(p.share for p in self.participants) != 100):
            raise ValueError('Commission participant shares must total 100%')
        if self.commission_fixed is not None and self.commission_percentage:
            raise ValueError('Choose fixed or percentage commission')
        allowed = {'hospital', *keys}
        if self.doctor_key:
            allowed.add(self.doctor_key)
        if set(self.discount_sharing) - allowed:
            raise ValueError('Discount responsibility references an unknown participant')
        return self


class PolicyCreate(BaseModel):
    scope: Literal['hospital', 'department', 'category', 'item', 'doctor', 'referrer']
    selector: str = Field(default='*', min_length=1, max_length=150)
    effective_from: datetime
    effective_until: datetime | None = None
    reason: str = Field(min_length=3, max_length=500)
    rules: FinancialRules

    @model_validator(mode='after')
    def valid_period(self):
        if self.effective_from.tzinfo is None or (self.effective_until and self.effective_until.tzinfo is None):
            raise ValueError('Effective dates require timezone offsets')
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError('Effective end must follow start')
        return self


class SettlementCreate(BaseModel):
    participant_key: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, decimal_places=2)
    request_key: str = Field(min_length=8, max_length=100)
    reason: str = Field(min_length=3, max_length=500)
    approve_pending: bool = False
