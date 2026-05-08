from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory import (
    InventoryCategory,
    InventoryRequisition,
    InventoryItem,
    InventoryStore,
    InventoryStoreItem,
    InventoryStockTransaction,
    PurchaseRequest,
    Reagent,
    ReagentBatch,
    ReagentUsage,
    StockAdjustment,
    StockBatch,
    StockIssue,
    StockReceiving,
    StockTransfer,
    Supplier,
    ReagentWastage,
    ReagentTestMapping,
)


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def paginate(self, stmt, *, page: int, page_size: int) -> tuple[list[Any], int]:
        total = int(self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
        items = list(self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique())
        return items, total

    def create(self, entity):
        self.db.add(entity)
        self.db.flush()
        return entity

    def list_items(self, branch_id=None, q=None, category_id=None, supplier_id=None, low_stock=False):
        stmt = select(InventoryItem).options(joinedload(InventoryItem.category), joinedload(InventoryItem.preferred_supplier)).where(InventoryItem.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(InventoryItem.name).like(pattern)
                | func.lower(func.coalesce(InventoryItem.item_code, "")).like(pattern)
                | func.lower(func.coalesce(InventoryItem.barcode, "")).like(pattern)
            )
        if category_id:
            stmt = stmt.where(InventoryItem.category_id == category_id)
        if supplier_id:
            stmt = stmt.where(InventoryItem.supplier_id == supplier_id)
        if low_stock:
            stmt = stmt.where(InventoryItem.stock_quantity <= InventoryItem.reorder_level)
        return stmt.order_by(InventoryItem.name.asc())

    def get_item(self, entity_id, *, for_update: bool = False):
        stmt = select(InventoryItem).options(joinedload(InventoryItem.category), joinedload(InventoryItem.preferred_supplier)).where(InventoryItem.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_supplier(self, entity_id):
        return self.db.get(Supplier, entity_id)

    def list_stores(self, branch_id=None, q=None, include_inactive=False):
        stmt = select(InventoryStore)
        if not include_inactive:
            stmt = stmt.where(InventoryStore.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryStore.branch_id == branch_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(InventoryStore.name).like(pattern)
                | func.lower(InventoryStore.code).like(pattern)
                | func.lower(func.coalesce(InventoryStore.department_name, "")).like(pattern)
                | func.lower(func.coalesce(InventoryStore.location, "")).like(pattern)
            )
        return stmt.order_by(InventoryStore.store_type.asc(), InventoryStore.name.asc())

    def get_store(self, entity_id, *, for_update: bool = False):
        stmt = select(InventoryStore).where(InventoryStore.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_main_store(self, branch_id=None):
        stmt = select(InventoryStore).where(InventoryStore.store_type == "main", InventoryStore.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryStore.branch_id == branch_id)
        return self.db.scalar(stmt.order_by(InventoryStore.created_at.asc()))

    def get_store_balance(self, store_id, item_id, *, for_update: bool = False):
        stmt = select(InventoryStoreItem).options(joinedload(InventoryStoreItem.store), joinedload(InventoryStoreItem.item)).where(
            InventoryStoreItem.store_id == store_id,
            InventoryStoreItem.item_id == item_id,
            InventoryStoreItem.is_active.is_(True),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def list_store_balances(self, branch_id=None, store_id=None, item_id=None, q=None, stock_status=None):
        stmt = select(InventoryStoreItem).options(
            joinedload(InventoryStoreItem.store),
            joinedload(InventoryStoreItem.item).joinedload(InventoryItem.category),
            joinedload(InventoryStoreItem.item).joinedload(InventoryItem.preferred_supplier),
        ).where(InventoryStoreItem.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryStoreItem.store.has(InventoryStore.branch_id == branch_id))
        if store_id:
            stmt = stmt.where(InventoryStoreItem.store_id == store_id)
        if item_id:
            stmt = stmt.where(InventoryStoreItem.item_id == item_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                InventoryStoreItem.item.has(func.lower(InventoryItem.name).like(pattern))
                | InventoryStoreItem.store.has(func.lower(InventoryStore.name).like(pattern))
            )
        if stock_status == "out":
            stmt = stmt.where(InventoryStoreItem.quantity_on_hand <= 0)
        elif stock_status == "low":
            stmt = stmt.where(InventoryStoreItem.quantity_on_hand > 0, InventoryStoreItem.quantity_on_hand <= InventoryStoreItem.reorder_level)
        return stmt.order_by(InventoryStoreItem.updated_at.desc())

    def list_suppliers(self, branch_id=None, q=None):
        stmt = select(Supplier).where(Supplier.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Supplier.branch_id == branch_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(Supplier.name).like(pattern)
                | func.lower(func.coalesce(Supplier.contact_person, "")).like(pattern)
                | func.lower(func.coalesce(Supplier.phone, "")).like(pattern)
            )
        return stmt.order_by(Supplier.name.asc())

    def list_receivings(self, branch_id=None, q=None):
        stmt = select(StockReceiving).options(joinedload(StockReceiving.item), joinedload(StockReceiving.supplier), joinedload(StockReceiving.store)).where(StockReceiving.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(StockReceiving.item.has(InventoryItem.branch_id == branch_id))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(StockReceiving.invoice_number).like(pattern)
                | func.lower(func.coalesce(StockReceiving.batch_no, "")).like(pattern)
                | func.lower(func.coalesce(StockReceiving.department, "")).like(pattern)
            )
        return stmt.order_by(StockReceiving.received_date.desc())

    def list_issues(self, branch_id=None, q=None):
        stmt = select(StockIssue).options(joinedload(StockIssue.item), joinedload(StockIssue.batch), joinedload(StockIssue.store)).where(StockIssue.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(StockIssue.item.has(InventoryItem.branch_id == branch_id))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(StockIssue.department, "")).like(pattern)
                | func.lower(func.coalesce(StockIssue.requestor, "")).like(pattern)
                | func.lower(func.coalesce(StockIssue.purpose, "")).like(pattern)
            )
        return stmt.order_by(StockIssue.issue_date.desc())

    def list_transfers(self, branch_id=None, q=None):
        stmt = select(StockTransfer).options(
            joinedload(StockTransfer.item),
            joinedload(StockTransfer.batch),
            joinedload(StockTransfer.source_store),
            joinedload(StockTransfer.destination_store),
            joinedload(StockTransfer.requested_by_user),
            joinedload(StockTransfer.approved_by_user),
            joinedload(StockTransfer.issued_by_user),
            joinedload(StockTransfer.received_by_user),
        ).where(StockTransfer.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(StockTransfer.item.has(InventoryItem.branch_id == branch_id))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(StockTransfer.source_location, "")).like(pattern)
                | func.lower(func.coalesce(StockTransfer.destination_location, "")).like(pattern))
        return stmt.order_by(StockTransfer.transfer_date.desc())

    def list_purchase_requests(self, branch_id=None, q=None):
        stmt = select(PurchaseRequest).options(joinedload(PurchaseRequest.item), joinedload(PurchaseRequest.supplier)).where(PurchaseRequest.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(PurchaseRequest.item.has(InventoryItem.branch_id == branch_id))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(PurchaseRequest.department, "")).like(pattern)
                | func.lower(func.coalesce(PurchaseRequest.priority, "")).like(pattern)
            )
        return stmt.order_by(PurchaseRequest.created_at.desc())

    def get_requisition(self, entity_id, *, for_update: bool = False):
        stmt = select(InventoryRequisition).options(
            joinedload(InventoryRequisition.item),
            joinedload(InventoryRequisition.source_store),
            joinedload(InventoryRequisition.destination_store),
            joinedload(InventoryRequisition.requested_by_user),
            joinedload(InventoryRequisition.approved_by_user),
            joinedload(InventoryRequisition.rejected_by_user),
            joinedload(InventoryRequisition.issued_by_user),
        ).where(InventoryRequisition.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def list_requisitions(self, branch_id=None, q=None, store_id=None, status=None):
        stmt = select(InventoryRequisition).options(
            joinedload(InventoryRequisition.item),
            joinedload(InventoryRequisition.source_store),
            joinedload(InventoryRequisition.destination_store),
            joinedload(InventoryRequisition.requested_by_user),
            joinedload(InventoryRequisition.approved_by_user),
            joinedload(InventoryRequisition.rejected_by_user),
            joinedload(InventoryRequisition.issued_by_user),
        ).where(InventoryRequisition.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryRequisition.destination_store.has(InventoryStore.branch_id == branch_id))
        if store_id:
            stmt = stmt.where((InventoryRequisition.source_store_id == store_id) | (InventoryRequisition.destination_store_id == store_id))
        if status:
            stmt = stmt.where(InventoryRequisition.status == status)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(InventoryRequisition.department, "")).like(pattern)
                | func.lower(func.coalesce(InventoryRequisition.priority, "")).like(pattern)
                | InventoryRequisition.item.has(func.lower(InventoryItem.name).like(pattern))
            )
        return stmt.order_by(InventoryRequisition.created_at.desc())

    def list_reagents(self, branch_id=None, q=None):
        stmt = select(Reagent).options(joinedload(Reagent.supplier)).where(Reagent.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Reagent.branch_id == branch_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(Reagent.name).like(pattern)
                | func.lower(func.coalesce(Reagent.reagent_code, "")).like(pattern)
            )
        return stmt.order_by(Reagent.name.asc())

    def get_reagent(self, entity_id, *, for_update: bool = False):
        stmt = select(Reagent).options(joinedload(Reagent.supplier)).where(Reagent.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_reagent_batch(self, entity_id, *, for_update: bool = False):
        stmt = select(ReagentBatch).where(ReagentBatch.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def list_reagent_batches(self, reagent_id=None, q=None):
        stmt = select(ReagentBatch).options(joinedload(ReagentBatch.reagent), joinedload(ReagentBatch.supplier)).where(ReagentBatch.is_active.is_(True))
        if reagent_id:
            stmt = stmt.where(ReagentBatch.reagent_id == reagent_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(ReagentBatch.batch_no, "")).like(pattern)
                | func.lower(func.coalesce(ReagentBatch.lot_number, "")).like(pattern)
            )
        return stmt.order_by(ReagentBatch.expiry_date.asc())

    def list_reagent_usage(self, reagent_id=None, q=None):
        stmt = select(ReagentUsage).options(joinedload(ReagentUsage.reagent), joinedload(ReagentUsage.batch)).where(ReagentUsage.is_active.is_(True))
        if reagent_id:
            stmt = stmt.where(ReagentUsage.reagent_id == reagent_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(ReagentUsage.test_name).like(pattern))
        return stmt.order_by(ReagentUsage.used_at.desc())

    def list_reagent_wastage(self, reagent_id=None, q=None):
        stmt = select(ReagentWastage).options(joinedload(ReagentWastage.reagent), joinedload(ReagentWastage.batch)).where(ReagentWastage.is_active.is_(True))
        if reagent_id:
            stmt = stmt.where(ReagentWastage.reagent_id == reagent_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(func.coalesce(ReagentWastage.reason, "")).like(pattern))
        return stmt.order_by(ReagentWastage.recorded_at.desc())

    def list_reagent_test_mappings(self, reagent_id=None):
        stmt = select(ReagentTestMapping).where(ReagentTestMapping.is_active.is_(True))
        if reagent_id:
            stmt = stmt.where(ReagentTestMapping.reagent_id == reagent_id)
        return stmt.order_by(ReagentTestMapping.test_name.asc())

    def get_category(self, entity_id):
        return self.db.get(InventoryCategory, entity_id)

    def get_purchase_request(self, entity_id):
        return self.db.get(PurchaseRequest, entity_id)

    def get_stock_batch(self, entity_id, *, for_update: bool = False):
        stmt = select(StockBatch).where(StockBatch.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def list_low_stock_items(self, branch_id=None):
        stmt = select(InventoryItem).where(InventoryItem.is_active.is_(True), InventoryItem.stock_quantity <= InventoryItem.reorder_level)
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        return stmt

    def list_near_expiry_batches(self, branch_id=None, cutoff_date: date | None = None):
        cutoff = cutoff_date or date.today()
        stmt = select(StockBatch).options(joinedload(StockBatch.item)).where(StockBatch.is_active.is_(True), StockBatch.expiry_date.is_not(None), StockBatch.expiry_date <= cutoff)
        if branch_id:
            stmt = stmt.where(StockBatch.item.has(InventoryItem.branch_id == branch_id))
        return stmt

    def list_expired_batches(self, branch_id=None):
        today = date.today()
        stmt = select(StockBatch).options(joinedload(StockBatch.item)).where(StockBatch.is_active.is_(True), StockBatch.expiry_date.is_not(None), StockBatch.expiry_date < today)
        if branch_id:
            stmt = stmt.where(StockBatch.item.has(InventoryItem.branch_id == branch_id))
        return stmt

    def get_reagent_usage_trend(self, days=7):
        return int(self.db.scalar(select(func.count(ReagentUsage.id)).where(ReagentUsage.is_active.is_(True))))
