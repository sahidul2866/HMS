from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class InventoryCategory(Base, BaseModelMixin):
    __tablename__ = "inventory_categories"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    parent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_categories.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    item_type: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    branch = relationship("Branch")
    parent = relationship("InventoryCategory", remote_side=lambda: [InventoryCategory.id])
    items = relationship("InventoryItem", back_populates="category")


class Supplier(Base, BaseModelMixin):
    __tablename__ = "suppliers"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    tax_number: Mapped[str | None] = mapped_column(String(80))
    payment_terms: Mapped[str | None] = mapped_column(String(120))
    rating: Mapped[int | None] = mapped_column(Numeric(2, 0))
    note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    branch = relationship("Branch")
    items = relationship("InventoryItem", back_populates="preferred_supplier")
    reagent_batches = relationship("ReagentBatch", back_populates="supplier")


class InventoryItem(Base, BaseModelMixin):
    __tablename__ = "inventory_items"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    category_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_categories.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    item_code: Mapped[str | None] = mapped_column(String(80), unique=True)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sub_category: Mapped[str | None] = mapped_column(String(120))
    item_type: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    unit_of_measurement: Mapped[str] = mapped_column(String(40), nullable=False, default="piece")
    is_batch_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    minimum_stock_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    maximum_stock_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    storage_location: Mapped[str | None] = mapped_column(String(120))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    stock_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_url: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    category = relationship("InventoryCategory", back_populates="items")
    preferred_supplier = relationship("Supplier", back_populates="items")
    batches = relationship("StockBatch", back_populates="item")
    receivings = relationship("StockReceiving", back_populates="item")
    issues = relationship("StockIssue", back_populates="item")
    transfers = relationship("StockTransfer", back_populates="item")
    adjustments = relationship("StockAdjustment", back_populates="item")
    purchase_requests = relationship("PurchaseRequest", back_populates="item")
    transactions = relationship("InventoryStockTransaction", back_populates="item")
    store_balances = relationship("InventoryStoreItem", back_populates="item")


class StockBatch(Base, BaseModelMixin):
    __tablename__ = "stock_batches"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    batch_no: Mapped[str | None] = mapped_column(String(120))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    manufacturing_date: Mapped[Date | None] = mapped_column(Date())
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(120))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    item = relationship("InventoryItem", back_populates="batches")
    store = relationship("InventoryStore", back_populates="batches")
    issues = relationship("StockIssue", back_populates="batch")
    transfers = relationship("StockTransfer", back_populates="batch")
    adjustments = relationship("StockAdjustment", back_populates="batch")
    transactions = relationship("InventoryStockTransaction", back_populates="batch")


class StockReceiving(Base, BaseModelMixin):
    __tablename__ = "stock_receivings"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    invoice_number: Mapped[str | None] = mapped_column(String(120))
    received_date: Mapped[Date] = mapped_column(Date(), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    batch_no: Mapped[str | None] = mapped_column(String(120))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    manufacturing_date: Mapped[Date | None] = mapped_column(Date())
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    item = relationship("InventoryItem", back_populates="receivings")
    store = relationship("InventoryStore", back_populates="receivings")
    supplier = relationship("Supplier")
    created_by_user = relationship("User", foreign_keys=[created_by])


class StockIssue(Base, BaseModelMixin):
    __tablename__ = "stock_issues"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    batch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_batches.id"))
    department: Mapped[str | None] = mapped_column(String(120))
    requestor: Mapped[str | None] = mapped_column(String(120))
    purpose: Mapped[str | None] = mapped_column(Text)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    issue_date: Mapped[Date] = mapped_column(Date(), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    item = relationship("InventoryItem", back_populates="issues")
    store = relationship("InventoryStore", back_populates="issues")
    batch = relationship("StockBatch", back_populates="issues")
    patient = relationship("Patient")
    visit = relationship("OPDVisit")
    created_by_user = relationship("User", foreign_keys=[created_by])


class StockTransfer(Base, BaseModelMixin):
    __tablename__ = "stock_transfers"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_batches.id"))
    source_store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    destination_store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    source_location: Mapped[str | None] = mapped_column(String(120))
    destination_location: Mapped[str | None] = mapped_column(String(120))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approved_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    issued_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    transfer_date: Mapped[Date] = mapped_column(Date(), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="requested")
    note: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    issued_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    received_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    item = relationship("InventoryItem", back_populates="transfers")
    batch = relationship("StockBatch", back_populates="transfers")
    source_store = relationship("InventoryStore", foreign_keys=[source_store_id], back_populates="outgoing_transfers")
    destination_store = relationship("InventoryStore", foreign_keys=[destination_store_id], back_populates="incoming_transfers")
    created_by_user = relationship("User", foreign_keys=[created_by])
    requested_by_user = relationship("User", foreign_keys=[requested_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    issued_by_user = relationship("User", foreign_keys=[issued_by])
    received_by_user = relationship("User", foreign_keys=[received_by])


class StockAdjustment(Base, BaseModelMixin):
    __tablename__ = "stock_adjustments"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_batches.id"))
    store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    adjustment_type: Mapped[str] = mapped_column(String(60), nullable=False)
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="posted")
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[date] = mapped_column(Date(), nullable=False)

    item = relationship("InventoryItem", back_populates="adjustments")
    batch = relationship("StockBatch", back_populates="adjustments")
    store = relationship("InventoryStore", back_populates="adjustments")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class PurchaseRequest(Base, BaseModelMixin):
    __tablename__ = "purchase_requests"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    department: Mapped[str | None] = mapped_column(String(120))
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    expected_date: Mapped[Date | None] = mapped_column(Date())
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="requested")
    note: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    item = relationship("InventoryItem", back_populates="purchase_requests")
    supplier = relationship("Supplier")
    requested_by_user = relationship("User", foreign_keys=[requested_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class InventoryStockTransaction(Base, BaseModelMixin):
    __tablename__ = "inventory_stock_transactions"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_batches.id"))
    store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    transaction_type: Mapped[str] = mapped_column(String(60), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(60))
    reference_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    stock_before: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    stock_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    item = relationship("InventoryItem", back_populates="transactions")
    batch = relationship("StockBatch", back_populates="transactions")
    store = relationship("InventoryStore", back_populates="transactions")
    created_by_user = relationship("User", foreign_keys=[created_by])


class InventoryStore(Base, BaseModelMixin):
    __tablename__ = "inventory_stores"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    parent_store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    store_type: Mapped[str] = mapped_column(String(60), nullable=False, default="sub_store")
    department_name: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(160))
    allow_sub_store_transfers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    department = relationship("Department")
    parent_store = relationship("InventoryStore", remote_side=lambda: [InventoryStore.id])
    balances = relationship("InventoryStoreItem", back_populates="store")
    batches = relationship("StockBatch", back_populates="store")
    receivings = relationship("StockReceiving", back_populates="store")
    issues = relationship("StockIssue", back_populates="store")
    adjustments = relationship("StockAdjustment", back_populates="store")
    transactions = relationship("InventoryStockTransaction", back_populates="store")
    outgoing_transfers = relationship("StockTransfer", foreign_keys=[StockTransfer.source_store_id], back_populates="source_store")
    incoming_transfers = relationship("StockTransfer", foreign_keys=[StockTransfer.destination_store_id], back_populates="destination_store")


class InventoryStoreItem(Base, BaseModelMixin):
    __tablename__ = "inventory_store_items"

    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"), nullable=False)
    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    minimum_stock_level: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    maximum_stock_level: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(160))

    store = relationship("InventoryStore", back_populates="balances")
    item = relationship("InventoryItem", back_populates="store_balances")


class InventoryRequisition(Base, BaseModelMixin):
    __tablename__ = "inventory_requisitions"

    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    source_store_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"))
    destination_store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_stores.id"), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approved_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    issued_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    required_date: Mapped[Date | None] = mapped_column(Date())
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft")
    remarks: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    rejected_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    issued_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    item = relationship("InventoryItem")
    source_store = relationship("InventoryStore", foreign_keys=[source_store_id])
    destination_store = relationship("InventoryStore", foreign_keys=[destination_store_id])
    requested_by_user = relationship("User", foreign_keys=[requested_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    rejected_by_user = relationship("User", foreign_keys=[rejected_by])
    issued_by_user = relationship("User", foreign_keys=[issued_by])


class Reagent(Base, BaseModelMixin):
    __tablename__ = "reagents"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    reagent_code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="other")
    test_mapping: Mapped[str | None] = mapped_column(Text)
    analyzer_mapping: Mapped[str | None] = mapped_column(Text)
    manufacturer: Mapped[str | None] = mapped_column(String(150))
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    storage_condition: Mapped[str | None] = mapped_column(String(80))
    opening_date: Mapped[Date | None] = mapped_column(Date())
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    closed_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    opened_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    stability_days: Mapped[int | None] = mapped_column(Numeric(5, 0))
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    supplier = relationship("Supplier")
    batches = relationship("ReagentBatch", back_populates="reagent")
    usage = relationship("ReagentUsage", back_populates="reagent")
    wastage = relationship("ReagentWastage", back_populates="reagent")
    test_mappings = relationship("ReagentTestMapping", back_populates="reagent")


class ReagentBatch(Base, BaseModelMixin):
    __tablename__ = "reagent_batches"

    reagent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reagents.id"), nullable=False)
    batch_no: Mapped[str | None] = mapped_column(String(120))
    lot_number: Mapped[str | None] = mapped_column(String(120))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    manufacturing_date: Mapped[Date | None] = mapped_column(Date())
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    quantity_available: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    quantity_opened: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    opened_at: Mapped[Date | None] = mapped_column(Date())
    stability_days: Mapped[int | None] = mapped_column(Numeric(5, 0))
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="in_use")
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    note: Mapped[str | None] = mapped_column(Text)

    reagent = relationship("Reagent", back_populates="batches")
    supplier = relationship("Supplier")
    usage = relationship("ReagentUsage", back_populates="batch")
    wastage = relationship("ReagentWastage", back_populates="batch")


class ReagentTestMapping(Base, BaseModelMixin):
    __tablename__ = "reagent_test_mappings"

    reagent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reagents.id"), nullable=False)
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    analyzer_name: Mapped[str | None] = mapped_column(String(150))
    volume_used_per_test: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    remark: Mapped[str | None] = mapped_column(Text)

    reagent = relationship("Reagent", back_populates="test_mappings")


class ReagentUsage(Base, BaseModelMixin):
    __tablename__ = "reagent_usage"

    reagent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reagents.id"), nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reagent_batches.id"))
    analyzer_name: Mapped[str | None] = mapped_column(String(150))
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    reagent_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    used_at: Mapped[Date] = mapped_column(Date(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    reagent = relationship("Reagent", back_populates="usage")
    batch = relationship("ReagentBatch", back_populates="usage")
    created_by_user = relationship("User")


class ReagentWastage(Base, BaseModelMixin):
    __tablename__ = "reagent_wastage"

    reagent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reagents.id"), nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reagent_batches.id"))
    wasted_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="discarded")
    recorded_at: Mapped[Date] = mapped_column(Date(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    reagent = relationship("Reagent", back_populates="wastage")
    batch = relationship("ReagentBatch", back_populates="wastage")
    created_by_user = relationship("User")
