from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10


class InventoryCategoryCreate(BaseModel):
    name: str = Field(max_length=150)
    description: str | None = Field(default=None)
    parent_id: UUID | None = None
    item_type: str = Field(default="general", max_length=60)
    is_active: bool = Field(default=True)


class InventoryCategoryRead(InventoryCategoryCreate):
    id: UUID
    created_at: date | datetime


class SupplierCreate(BaseModel):
    name: str = Field(max_length=200)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None)
    tax_number: str | None = Field(default=None, max_length=80)
    payment_terms: str | None = Field(default=None, max_length=120)
    rating: int | None = Field(default=None, ge=0, le=5)
    note: str | None = Field(default=None)
    is_active: bool = Field(default=True)


class SupplierRead(SupplierCreate):
    id: UUID
    created_at: date | datetime


class InventoryItemCreate(BaseModel):
    name: str = Field(max_length=200)
    item_code: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=100)
    category_id: UUID | None = None
    supplier_id: UUID | None = None
    sub_category: str | None = Field(default=None, max_length=120)
    item_type: str = Field(default="general", max_length=60)
    unit_of_measurement: str = Field(default="piece", max_length=40)
    is_batch_tracked: bool = Field(default=True)
    reorder_level: Decimal = Field(default=0, ge=0)
    minimum_stock_level: Decimal = Field(default=0, ge=0)
    maximum_stock_level: Decimal = Field(default=0, ge=0)
    storage_location: str | None = Field(default=None, max_length=120)
    tax_rate: Decimal | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)


class InventoryItemRead(InventoryItemCreate):
    id: UUID
    stock_quantity: Decimal
    stock_value: Decimal
    category_name: str | None = None
    supplier_name: str | None = None
    store_balances: list["InventoryStoreBalanceRead"] = Field(default_factory=list)
    created_at: date | datetime


class InventoryStoreCreate(BaseModel):
    code: str = Field(max_length=80)
    name: str = Field(max_length=160)
    store_type: str = Field(default="sub_store", max_length=60)
    department_id: UUID | None = None
    parent_store_id: UUID | None = None
    department_name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    allow_sub_store_transfers: bool = Field(default=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)


class InventoryStoreRead(InventoryStoreCreate):
    id: UUID
    current_stock_value: Decimal = Field(default=0)
    total_items: int = 0
    low_stock_items: int = 0
    created_at: date | datetime


class InventoryStoreBalanceRead(BaseModel):
    id: UUID
    store_id: UUID
    store_name: str
    store_type: str
    department_name: str | None = None
    item_id: UUID
    item_name: str
    item_code: str | None = None
    category_name: str | None = None
    supplier_name: str | None = None
    quantity_on_hand: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    reorder_level: Decimal
    minimum_stock_level: Decimal
    maximum_stock_level: Decimal
    location: str | None = None
    stock_status: str
    expiry_status: str | None = None


class StockBatchCreate(BaseModel):
    item_id: UUID
    store_id: UUID | None = None
    batch_no: str | None = Field(default=None, max_length=120)
    expiry_date: date | None = None
    manufacturing_date: date | None = None
    quantity: Decimal = Field(default=0, ge=0)
    location: str | None = Field(default=None, max_length=120)
    unit_cost: Decimal = Field(default=0, ge=0)
    total_cost: Decimal = Field(default=0, ge=0)
    notes: str | None = Field(default=None)


class StockBatchRead(StockBatchCreate):
    id: UUID
    created_at: date | datetime


class StockReceivingCreate(BaseModel):
    item_id: UUID
    store_id: UUID | None = None
    supplier_id: UUID | None = None
    invoice_number: str | None = Field(default=None, max_length=120)
    received_date: date
    department: str | None = Field(default=None, max_length=120)
    batch_no: str | None = Field(default=None, max_length=120)
    expiry_date: date | None = None
    manufacturing_date: date | None = None
    quantity: Decimal = Field(default=0, gt=0)
    unit_cost: Decimal = Field(default=0, ge=0)
    total_cost: Decimal = Field(default=0, ge=0)
    note: str | None = Field(default=None)
    location: str | None = Field(default=None, max_length=120)


class StockReceivingRead(StockReceivingCreate):
    id: UUID
    item_name: str | None = None
    store_name: str | None = None
    supplier_name: str | None = None
    created_at: date | datetime


class StockIssueCreate(BaseModel):
    item_id: UUID
    store_id: UUID | None = None
    batch_id: UUID | None = None
    department: str | None = Field(default=None, max_length=120)
    requestor: str | None = Field(default=None, max_length=120)
    purpose: str | None = Field(default=None)
    patient_id: UUID | None = None
    visit_id: UUID | None = None
    quantity: Decimal = Field(default=0, gt=0)
    issue_date: date
    note: str | None = Field(default=None)


class StockIssueRead(StockIssueCreate):
    id: UUID
    item_name: str | None = None
    store_name: str | None = None
    batch_no: str | None = None
    created_at: date | datetime


class StockTransferCreate(BaseModel):
    item_id: UUID
    batch_id: UUID | None = None
    source_store_id: UUID | None = None
    destination_store_id: UUID | None = None
    source_location: str | None = Field(default=None, max_length=120)
    destination_location: str | None = Field(default=None, max_length=120)
    quantity: Decimal = Field(default=0, gt=0)
    requested_quantity: Decimal | None = Field(default=None, gt=0)
    approved_quantity: Decimal | None = Field(default=None, ge=0)
    issued_quantity: Decimal | None = Field(default=None, ge=0)
    received_quantity: Decimal | None = Field(default=None, ge=0)
    transfer_date: date
    status: str = Field(default="requested", max_length=60)
    note: str | None = Field(default=None)


class StockTransferRead(StockTransferCreate):
    id: UUID
    item_name: str | None = None
    batch_no: str | None = None
    source_store_name: str | None = None
    destination_store_name: str | None = None
    requested_by_name: str | None = None
    approved_by_name: str | None = None
    issued_by_name: str | None = None
    received_by_name: str | None = None
    created_at: date | datetime


class StockAdjustmentCreate(BaseModel):
    item_id: UUID
    batch_id: UUID | None = None
    store_id: UUID | None = None
    adjustment_type: str = Field(max_length=60)
    quantity_change: Decimal = Field(gt=0)
    reason: str | None = Field(default=None)
    note: str | None = Field(default=None)
    status: str = Field(default="posted", max_length=60)
    created_at: date | datetime


class StockAdjustmentRead(StockAdjustmentCreate):
    id: UUID
    item_name: str | None = None
    batch_no: str | None = None
    store_name: str | None = None


class InventoryRequisitionCreate(BaseModel):
    item_id: UUID
    source_store_id: UUID | None = None
    destination_store_id: UUID
    department: str | None = Field(default=None, max_length=120)
    requested_quantity: Decimal = Field(default=0, gt=0)
    approved_quantity: Decimal | None = Field(default=None, ge=0)
    issued_quantity: Decimal | None = Field(default=None, ge=0)
    priority: str = Field(default="normal", max_length=40)
    required_date: date | None = None
    reason: str | None = Field(default=None)
    status: str = Field(default="requested", max_length=60)
    remarks: str | None = Field(default=None)


class InventoryRequisitionRead(InventoryRequisitionCreate):
    id: UUID
    item_name: str | None = None
    source_store_name: str | None = None
    destination_store_name: str | None = None
    requested_by_name: str | None = None
    approved_by_name: str | None = None
    rejected_by_name: str | None = None
    issued_by_name: str | None = None
    created_at: date | datetime


class PurchaseRequestCreate(BaseModel):
    item_id: UUID
    supplier_id: UUID | None = None
    department: str | None = Field(default=None, max_length=120)
    requested_quantity: Decimal = Field(default=0, gt=0)
    priority: str = Field(default="normal", max_length=40)
    expected_date: date | None = None
    status: str = Field(default="requested", max_length=40)
    note: str | None = Field(default=None)


class PurchaseRequestRead(PurchaseRequestCreate):
    id: UUID
    item_name: str | None = None
    supplier_name: str | None = None
    requested_by_name: str | None = None
    approved_by_name: str | None = None
    created_at: date | datetime


class ReagentCreate(BaseModel):
    reagent_code: str = Field(max_length=120)
    name: str = Field(max_length=200)
    category: str = Field(default="other", max_length=80)
    test_mapping: str | None = Field(default=None)
    analyzer_mapping: str | None = Field(default=None)
    manufacturer: str | None = Field(default=None, max_length=150)
    supplier_id: UUID | None = None
    storage_condition: str | None = Field(default=None, max_length=80)
    opening_date: date | None = None
    opening_balance: Decimal | None = Field(default=None, ge=0)
    opened_balance: Decimal | None = Field(default=0, ge=0)
    closed_balance: Decimal | None = Field(default=0, ge=0)
    stability_days: int | None = Field(default=None, ge=0)
    status: str = Field(default="active", max_length=60)
    note: str | None = Field(default=None)


class ReagentRead(ReagentCreate):
    id: UUID
    supplier_name: str | None = None
    created_at: date | datetime


class ReagentBatchCreate(BaseModel):
    reagent_id: UUID
    batch_no: str | None = Field(default=None, max_length=120)
    lot_number: str | None = Field(default=None, max_length=120)
    expiry_date: date | None = None
    manufacturing_date: date | None = None
    quantity_received: Decimal = Field(default=0, gt=0)
    quantity_available: Decimal = Field(default=0, ge=0)
    quantity_opened: Decimal | None = Field(default=None, ge=0)
    opened_at: date | None = None
    stability_days: int | None = Field(default=None, ge=0)
    status: str = Field(default="in_use", max_length=60)
    supplier_id: UUID | None = None
    note: str | None = Field(default=None)


class ReagentBatchRead(ReagentBatchCreate):
    id: UUID
    reagent_name: str | None = None
    supplier_name: str | None = None
    created_at: date | datetime


class ReagentTestMappingCreate(BaseModel):
    reagent_id: UUID
    test_name: str = Field(max_length=200)
    analyzer_name: str | None = Field(default=None, max_length=150)
    volume_used_per_test: Decimal | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None)


class ReagentTestMappingRead(ReagentTestMappingCreate):
    id: UUID
    reagent_name: str | None = None
    created_at: date | datetime


class ReagentUsageCreate(BaseModel):
    reagent_id: UUID
    batch_id: UUID | None = None
    analyzer_name: str | None = Field(default=None, max_length=150)
    test_name: str = Field(max_length=200)
    quantity_used: Decimal = Field(default=0, gt=0)
    reagent_cost: Decimal | None = Field(default=None, ge=0)
    used_at: date
    note: str | None = Field(default=None)


class ReagentUsageRead(ReagentUsageCreate):
    id: UUID
    reagent_name: str | None = None
    batch_no: str | None = None
    created_by_name: str | None = None
    created_at: date | datetime


class ReagentWastageCreate(BaseModel):
    reagent_id: UUID
    batch_id: UUID | None = None
    wasted_quantity: Decimal = Field(default=0, gt=0)
    reason: str | None = Field(default=None)
    status: str = Field(default="discarded", max_length=60)
    recorded_at: date
    note: str | None = Field(default=None)


class ReagentWastageRead(ReagentWastageCreate):
    id: UUID
    reagent_name: str | None = None
    batch_no: str | None = None
    created_by_name: str | None = None
    created_at: date | datetime


class InventoryDashboardSummaryRead(BaseModel):
    total_stock_value: Decimal
    total_items: int
    low_stock_items: int
    out_of_stock_items: int
    near_expiry_items: int
    recent_receivings: int
    recent_issues: int
    category_counts: dict[str, int] = Field(default_factory=dict)
    total_stores: int = 0
    open_requisitions: int = 0
    open_transfers: int = 0
    store_stock_value: dict[str, Decimal] = Field(default_factory=dict)


class InventoryReportRead(BaseModel):
    low_stock_items: int
    near_expiry_batches: int
    expired_batches: int
    reagent_usage_last_7_days: int
    purchase_requests_open: int
    open_requisitions: int = 0
    open_transfers: int = 0
    adjustment_count: int = 0
