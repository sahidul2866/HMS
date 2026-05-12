from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MasterEntityBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None


class PharmacyMedicineTypeCreate(MasterEntityBase):
    pass


class PharmacyMedicineTypeUpdate(MasterEntityBase):
    pass


class PharmacyMedicineTypeRead(MasterEntityBase):
    id: UUID
    created_at: date | None = None

    model_config = {"from_attributes": True}


class PharmacyGenericCreate(MasterEntityBase):
    pass


class PharmacyGenericUpdate(MasterEntityBase):
    pass


class PharmacyGenericRead(MasterEntityBase):
    id: UUID

    model_config = {"from_attributes": True}


class PharmacyCompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=120)
    address: str | None = None
    note: str | None = None


class PharmacyCompanyUpdate(PharmacyCompanyCreate):
    pass


class PharmacyCompanyRead(PharmacyCompanyCreate):
    id: UUID

    model_config = {"from_attributes": True}


class PharmacyCustomerCreate(BaseModel):
    patient_id: UUID | None = None
    name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=120)
    address: str | None = None
    note: str | None = None


class PharmacyCustomerUpdate(PharmacyCustomerCreate):
    pass


class PharmacyCustomerRead(PharmacyCustomerCreate):
    id: UUID
    customer_number: str
    patient_name: str | None = None
    patient_number: str | None = None

    model_config = {"from_attributes": True}


class PharmacyMedicineCreate(BaseModel):
    medicine_type_id: UUID
    generic_id: UUID
    company_id: UUID
    name: str = Field(min_length=2, max_length=150)
    strength: str | None = Field(default=None, max_length=60)
    dosage_form: str | None = Field(default=None, max_length=60)
    sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    purchase_price: Decimal = Field(default=0, ge=0)
    sale_price: Decimal = Field(default=0, ge=0)
    reorder_level: Decimal = Field(default=0, ge=0)
    description: str | None = None


class PharmacyMedicineUpdate(PharmacyMedicineCreate):
    pass


class PharmacyMedicineRead(PharmacyMedicineCreate):
    id: UUID
    stock_quantity: Decimal
    medicine_type_name: str
    generic_name: str
    company_name: str

    model_config = {"from_attributes": True}


class PharmacyPurchaseCreate(BaseModel):
    medicine_id: UUID
    purchase_date: date
    supplier_name: str | None = Field(default=None, max_length=150)
    invoice_number: str | None = Field(default=None, max_length=80)
    batch_no: str | None = Field(default=None, max_length=80)
    expiry_date: date | None = None
    quantity: Decimal = Field(gt=0)
    bonus_quantity: Decimal = Field(default=0, ge=0)
    unit_cost: Decimal = Field(gt=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    note: str | None = None


class PharmacyPurchaseUpdate(PharmacyPurchaseCreate):
    pass


class PharmacyPurchaseRead(PharmacyPurchaseCreate):
    id: UUID
    purchase_number: str
    total_amount: Decimal
    medicine_name: str
    purchased_by_name: str | None = None

    model_config = {"from_attributes": True}


class PharmacySaleItemWrite(BaseModel):
    medicine_id: UUID
    source_visit_order_id: UUID | None = None
    batch_no: str | None = Field(default=None, max_length=80)
    expiry_date: date | None = None
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    note: str | None = None


class PharmacySaleCreate(BaseModel):
    customer_id: UUID | None = None
    patient_id: UUID | None = None
    source_visit_id: UUID | None = None
    sale_date: date
    discount_amount: Decimal = Field(default=0, ge=0)
    note: str | None = None
    items: list[PharmacySaleItemWrite] = Field(min_length=1)


class PharmacySaleUpdate(PharmacySaleCreate):
    pass


class PharmacySaleItemRead(BaseModel):
    id: UUID
    medicine_id: UUID
    source_visit_order_id: UUID | None = None
    medicine_name: str
    batch_no: str | None = None
    expiry_date: date | None = None
    quantity: Decimal
    returned_quantity: Decimal
    available_return_quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    note: str | None = None


class PharmacySaleRead(BaseModel):
    id: UUID
    customer_id: UUID
    patient_id: UUID | None = None
    source_visit_id: UUID | None = None
    sale_number: str
    sale_date: date
    customer_name: str
    patient_name: str | None = None
    subtotal: Decimal
    discount_amount: Decimal
    return_amount: Decimal
    net_payable: Decimal
    status: str
    note: str | None = None
    sold_by_name: str | None = None
    items: list[PharmacySaleItemRead] = []


class PharmacySaleReturnCreate(BaseModel):
    sale_id: UUID
    sale_item_id: UUID
    returned_at: date
    quantity: Decimal = Field(gt=0)
    note: str | None = None


class PharmacySaleReturnUpdate(BaseModel):
    returned_at: date
    quantity: Decimal = Field(gt=0)
    note: str | None = None


class PharmacySaleReturnRead(BaseModel):
    id: UUID
    sale_id: UUID
    sale_item_id: UUID
    customer_id: UUID
    medicine_id: UUID
    return_number: str
    sale_number: str
    customer_name: str
    medicine_name: str
    batch_no: str | None = None
    expiry_date: date | None = None
    returned_at: date
    quantity: Decimal
    unit_price: Decimal
    total_amount: Decimal
    note: str | None = None
    returned_by_name: str | None = None


class PharmacyInvestigationSettingCreate(BaseModel):
    category_name: str = Field(min_length=2, max_length=120)
    test_name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=80)
    service_area: str = Field(min_length=2, max_length=60, pattern="^(laboratory|radiology)$")
    fee: Decimal = Field(default=0, ge=0)
    room_number: str | None = Field(default=None, max_length=60)
    normal_range: str | None = Field(default=None, max_length=180)
    unit: str | None = Field(default=None, max_length=60)
    description: str | None = None
    specimen_type: str | None = Field(default=None, max_length=120)
    turnaround_time: str | None = Field(default=None, max_length=120)
    report_header: str | None = None
    report_template: str | None = None
    report_note_template: str | None = None
    requires_report: bool = True
    is_active: bool = True


class PharmacyInvestigationSettingUpdate(PharmacyInvestigationSettingCreate):
    pass


class PharmacyInvestigationSettingRead(PharmacyInvestigationSettingCreate):
    id: UUID

    model_config = {"from_attributes": True}


class PharmacyInvestigationItemWrite(BaseModel):
    setting_id: UUID
    source_visit_order_id: UUID | None = None
    status: str = Field(default="ordered", min_length=2, max_length=30)
    fee: Decimal | None = Field(default=None, ge=0)
    result_text: str | None = None
    note: str | None = None


class PharmacyInvestigationCreate(BaseModel):
    customer_id: UUID | None = None
    patient_id: UUID | None = None
    source_visit_id: UUID | None = None
    ordered_at: date
    status: str = Field(default="ordered", min_length=2, max_length=30)
    discount_amount: Decimal = Field(default=0, ge=0)
    report_note: str | None = None
    note: str | None = None
    report_title: str | None = Field(default=None, max_length=180)
    report_footer_note: str | None = None
    printable_schema: str | None = None
    items: list[PharmacyInvestigationItemWrite] = Field(min_length=1)


class PharmacyInvestigationUpdate(PharmacyInvestigationCreate):
    pass


class PharmacyInvestigationItemRead(BaseModel):
    id: UUID
    setting_id: UUID
    source_visit_order_id: UUID | None = None
    test_name: str
    setting_code: str
    category_name: str
    service_area: str
    status: str
    fee: Decimal
    result_text: str | None = None
    note: str | None = None
    normal_range: str | None = None
    unit: str | None = None
    description: str | None = None
    report_header: str | None = None
    report_template: str | None = None
    report_note_template: str | None = None
    requires_report: bool


class PharmacyInvestigationRead(BaseModel):
    id: UUID
    customer_id: UUID | None = None
    patient_id: UUID | None = None
    source_visit_id: UUID | None = None
    investigation_number: str
    ordered_at: date
    status: str
    fee: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    report_note: str | None = None
    note: str | None = None
    report_title: str | None = None
    report_footer_note: str | None = None
    printable_schema: str | None = None
    customer_name: str | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    setting_name: str | None = None
    setting_code: str | None = None
    category_name: str | None = None
    service_area: str | None = None
    test_count: int
    items: list[PharmacyInvestigationItemRead] = []


class PharmacyDispenseCreate(BaseModel):
    patient_id: UUID | None = None
    branch_id: UUID | None = None
    billing_invoice_id: UUID | None = None
    billing_invoice_item_id: UUID | None = None
    source_visit_id: UUID | None = None
    source_visit_order_id: UUID | None = None
    prescription_ref: str | None = None
    medicine_name: str = Field(min_length=2, max_length=150)
    quantity: Decimal
    unit_price: Decimal
    note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_uuid_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key in ("patient_id", "branch_id", "billing_invoice_id", "billing_invoice_item_id", "source_visit_id", "source_visit_order_id"):
                if data.get(key) in {"", "null", "undefined"}:
                    data[key] = None
            if isinstance(data.get("medicine_name"), str):
                data["medicine_name"] = data["medicine_name"].strip()
            if data.get("unit_price") in {"", None}:
                data["unit_price"] = Decimal("0")
        return data


class PharmacyDispenseReturnCreate(BaseModel):
    quantity: Decimal = Field(gt=0)
    note: str | None = None


class PharmacyDispenseRead(BaseModel):
    id: UUID
    patient_id: UUID | None = None
    billing_invoice_id: UUID | None = None
    billing_invoice_item_id: UUID | None = None
    billing_invoice_number: str | None = None
    billing_payment_status: str | None = None
    source_visit_id: UUID | None = None
    source_visit_order_id: UUID | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    visit_number: str | None = None
    medicine_name: str
    requested_quantity: Decimal | None = None
    quantity: Decimal
    returned_quantity: Decimal
    remaining_quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    status: str
    prescription_ref: str | None = None
    note: str | None = None
    return_note: str | None = None
    dispensed_at: str
    dispensed_by_name: str | None = None

    model_config = {"from_attributes": True}


class PharmacyPendingPrescriptionRead(BaseModel):
    order_id: UUID
    visit_id: UUID
    visit_number: str
    patient_id: UUID
    patient_number: str
    patient_name: str
    doctor_name: str
    visit_date: str
    visit_status: str
    item_name: str
    quantity: Decimal
    dispensed_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("0")
    instructions: str | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None
    prescription_status: str = "pending"
    payment_status: str | None = None
    availability_status: str = "unknown"
    available_quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")
    preferred_batch_no: str | None = None
    preferred_expiry_date: date | None = None
    available_stores: list[str] = []


class PharmacyDraftMedicineSuggestionRead(BaseModel):
    medicine_id: UUID
    medicine_name: str
    generic_name: str | None = None
    company_name: str | None = None
    stock_quantity: Decimal
    sale_price: Decimal
    match_reason: str | None = None


class PharmacySalesDraftItemRead(BaseModel):
    source_visit_order_id: UUID
    source_label: str
    quantity: Decimal
    medicine_suggestions: list[PharmacyDraftMedicineSuggestionRead]
    instruction: str | None = None
    warning: str | None = None


class PharmacySalesDraftRead(BaseModel):
    patient_id: UUID
    patient_name: str
    customer_id: UUID | None = None
    source_visit_id: UUID
    source_visit_number: str
    note: str | None = None
    items: list[PharmacySalesDraftItemRead]
    message: str | None = None


class PharmacyInvestigationDraftItemRead(BaseModel):
    source_visit_order_id: UUID
    setting_id: UUID | None = None
    test_name: str
    category_name: str | None = None
    service_area: str
    fee: Decimal | None = None
    instruction: str | None = None
    warning: str | None = None


class PharmacyInvestigationDraftRead(BaseModel):
    patient_id: UUID
    patient_name: str
    customer_id: UUID | None = None
    source_visit_id: UUID
    source_visit_number: str
    report_title: str | None = None
    note: str | None = None
    items: list[PharmacyInvestigationDraftItemRead]
    message: str | None = None


class PharmacySummaryRead(BaseModel):
    total_dispenses: int
    today_dispenses: int
    pending_prescriptions: int
    billed_prescriptions: int
    partial_dispenses: int
    returned_dispenses: int


class PharmacyDashboardSummaryRead(BaseModel):
    total_medicines: int
    low_stock_medicines: int
    total_customers: int
    total_sales: int
    total_returns: int
    total_investigations: int


class PharmacyStockMovementRead(BaseModel):
    id: UUID
    medicine_id: UUID
    medicine_name: str
    movement_type: str
    reference_type: str
    reference_id: UUID | None = None
    quantity_change: Decimal
    stock_before: Decimal
    stock_after: Decimal
    batch_no: str | None = None
    expiry_date: date | None = None
    unit_cost: Decimal | None = None
    sale_price: Decimal | None = None
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PharmacyMedicineBatchAvailabilityRead(BaseModel):
    store_id: UUID | None = None
    store_name: str | None = None
    store_type: str | None = None
    department_name: str | None = None
    batch_id: UUID | None = None
    batch_no: str | None = None
    expiry_date: date | None = None
    available_quantity: Decimal
    reserved_quantity: Decimal = Decimal("0")
    is_expired: bool = False
    is_near_expiry: bool = False
    source: str = "pharmacy"


class PharmacyMedicineAvailabilityRead(BaseModel):
    medicine_name: str
    pharmacy_medicine_id: UUID | None = None
    inventory_item_id: UUID | None = None
    total_available_quantity: Decimal
    total_reserved_quantity: Decimal
    pharmacy_stock_quantity: Decimal
    status: str
    preferred_batch_id: UUID | None = None
    preferred_batch_no: str | None = None
    preferred_expiry_date: date | None = None
    batches: list[PharmacyMedicineBatchAvailabilityRead] = []
