from datetime import datetime
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.patient import PatientRead


class BillingServiceCreate(BaseModel):
    branch_id: UUID | None = None
    service_code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    unit_price: Decimal = Field(gt=0)
    doctor_share_percentage: Decimal = Field(ge=0, le=100)


class BillingServiceRead(BillingServiceCreate):
    id: UUID
    is_active: bool

    model_config = {"from_attributes": True}


class ReferredDoctorCreate(BaseModel):
    branch_id: UUID | None = None
    doctor_code: str = Field(min_length=2, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    specialty: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)


class ReferredDoctorRead(ReferredDoctorCreate):
    id: UUID
    is_active: bool

    model_config = {"from_attributes": True}


class BillingInvoiceItemCreate(BaseModel):
    billing_service_id: UUID
    quantity: Decimal = Field(gt=0)


class BillingInvoiceCreate(BaseModel):
    branch_id: UUID | None = None
    patient_id: UUID
    referred_doctor_id: UUID | None = None
    referred_doctor_name: str | None = Field(default=None, max_length=150)
    discount_percentage: Decimal = Field(default=0, ge=0, le=100)
    note: str | None = None
    items: list[BillingInvoiceItemCreate] = Field(min_length=1)


class BillingInvoiceItemRead(BaseModel):
    id: UUID
    billing_service_id: UUID
    service_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    doctor_share_percentage: Decimal
    doctor_share_amount: Decimal

    model_config = {"from_attributes": True}


class BillingInvoiceRead(BaseModel):
    id: UUID
    invoice_number: str
    patient_id: UUID
    patient: PatientRead
    referred_doctor_id: UUID | None = None
    referred_doctor_name: str | None = None
    status: str
    void_reason: str | None = None
    voided_at: datetime | None = None
    sub_total: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    referred_doctor_amount: Decimal
    note: str | None = None
    created_at: datetime
    items: list[BillingInvoiceItemRead]

    model_config = {"from_attributes": True}


class BillingInvoiceListItem(BaseModel):
    id: UUID
    invoice_number: str
    patient_id: UUID
    patient: PatientRead
    referred_doctor_id: UUID | None = None
    status: str
    total_amount: Decimal
    referred_doctor_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingInvoiceFilterParams(BaseModel):
    q: str | None = None
    referred_doctor_id: UUID | None = None
    status: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class BillingSummaryRead(BaseModel):
    posted_invoice_count: int
    void_invoice_count: int
    gross_amount: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    referred_doctor_amount: Decimal


class BillingReferralSummaryRead(BaseModel):
    referred_doctor_id: UUID | None = None
    referred_doctor_name: str
    invoice_count: int
    net_amount: Decimal
    referred_doctor_amount: Decimal


class BillingInvoiceVoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class BillingInvoicePreview(BaseModel):
    sub_total: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    referred_doctor_amount: Decimal


class BillingInvoicePreviewRequest(BaseModel):
    discount_percentage: Decimal = Field(default=0, ge=0, le=100)
    items: list[BillingInvoiceItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> "BillingInvoicePreviewRequest":
        if not self.items:
            raise ValueError("At least one billing item is required")
        return self
