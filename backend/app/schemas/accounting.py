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

