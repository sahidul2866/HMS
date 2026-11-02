from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)
    evidence_reference: str = Field(min_length=3, max_length=200)

    @field_validator('reason', 'evidence_reference', check_fields=False)
    @classmethod
    def strip_text(cls, value):
        if len(value.strip()) < 3:
            raise ValueError('Enter a meaningful reason or evidence reference')
        return value.strip()


class StockCountCreate(Evidence):
    batch_id: UUID
    counted_quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class LegacyReturnAllocation(Evidence):
    dispense_id: UUID
    source_issue_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    disposition: Literal['historically_restocked', 'held_for_disposal', 'historically_disposed']


class DisposalCreate(Evidence):
    dispense_id: UUID
    receipt_id: UUID
    method: str = Field(min_length=3, max_length=200)
    witness: str = Field(min_length=3, max_length=150)
    performed_at: str = Field(min_length=10, max_length=40)


class ReviewDecision(BaseModel):
    decision: Literal['approve', 'reject']
    note: str = Field(min_length=5, max_length=2000)

    @field_validator('note')
    @classmethod
    def note_required(cls, value):
        if len(value.strip()) < 5:
            raise ValueError('Explain your review decision')
        return value.strip()
