from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Type
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
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
    ReagentWastage,
    ReagentTestMapping,
    StockAdjustment,
    StockBatch,
    StockIssue,
    StockReceiving,
    StockTransfer,
    Supplier,
)
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.inventory.repository import InventoryRepository
from app.schemas.inventory import (
    InventoryCategoryCreate,
    InventoryCategoryRead,
    InventoryDashboardSummaryRead,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryReportRead,
    InventoryRequisitionCreate,
    InventoryRequisitionRead,
    InventoryStoreBalanceRead,
    InventoryStoreCreate,
    InventoryStoreRead,
    PurchaseRequestCreate,
    PurchaseRequestRead,
    ReagentBatchCreate,
    ReagentBatchRead,
    ReagentCreate,
    ReagentRead,
    ReagentUsageCreate,
    ReagentUsageRead,
    ReagentWastageCreate,
    ReagentWastageRead,
    ReagentTestMappingCreate,
    StockAdjustmentCreate,
    StockAdjustmentRead,
    StockBatchCreate,
    StockBatchRead,
    StockIssueCreate,
    StockIssueRead,
    StockReceivingCreate,
    StockReceivingRead,
    StockTransferCreate,
    StockTransferRead,
    SupplierCreate,
    SupplierRead,
)


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)

    def _normalize_pagination(self, page: int, page_size: int) -> tuple[int, int]:
        return max(page, 1), min(max(page_size, 1), 100)

    def _paginate(self, stmt, *, page: int, page_size: int):
        page, page_size = self._normalize_pagination(page, page_size)
        items, total = self.repository.paginate(stmt, page=page, page_size=page_size)
        return items, total

    def _commit_and_log(self, *, actor: User, action: str, entity_type: str | None, entity_id: str | None, detail: dict | None, context: dict[str, str | None]):
        AuditService(self.db).log(
            user_id=actor.id,
            action=action,
            module="inventory",
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            context=context,
        )
        self.db.commit()

    def _normalize_text(self, value: str | None) -> str | None:
        normalized = (value or "").strip()
        return normalized or None

    def _ensure_branch_scope(self, entity, actor: User):
        branch_id = getattr(entity, "branch_id", None)
        if actor.branch_id and branch_id and actor.branch_id != branch_id:
            raise AppException(403, "forbidden", "Record belongs to a different branch")

    def _ensure_default_stores(self, actor: User) -> InventoryStore:
        main = self.repository.get_main_store(actor.branch_id)
        if main:
            self._backfill_main_store_balances(main, actor)
            return main
        names = [
            ("MAIN", "Main Inventory", "main", None),
            ("PHARMACY", "Pharmacy Store", "sub_store", "Pharmacy"),
            ("OPD", "OPD Store", "sub_store", "OPD"),
            ("IPD", "IPD Store", "sub_store", "IPD"),
            ("ER", "ER Store", "sub_store", "ER"),
            ("LAB", "Lab Store", "sub_store", "Laboratory"),
            ("RAD", "Radiology Store", "sub_store", "Radiology"),
            ("OT", "OT/Surgery Store", "sub_store", "OT/Surgery"),
            ("WARD", "Ward Store", "sub_store", "Ward"),
            ("ADMIN", "Admin/General Store", "sub_store", "Admin"),
        ]
        created: dict[str, InventoryStore] = {}
        for code, name, store_type, department in names:
            store = InventoryStore(
                id=uuid4(),
                branch_id=actor.branch_id,
                code=code,
                name=name,
                store_type=store_type,
                department_name=department,
                parent_store_id=created["MAIN"].id if store_type != "main" and "MAIN" in created else None,
                location=name,
                allow_sub_store_transfers=True,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create(store)
            created[code] = store
        self.db.flush()
        self._backfill_main_store_balances(created["MAIN"], actor)
        return created["MAIN"]

    def _backfill_main_store_balances(self, main: InventoryStore, actor: User) -> None:
        stmt = select(InventoryItem).where(InventoryItem.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(InventoryItem.branch_id == actor.branch_id)
        for item in self.db.scalars(stmt).all():
            if Decimal(item.stock_quantity or 0) <= 0:
                continue
            if self.repository.get_store_balance(main.id, item.id):
                continue
            balance = InventoryStoreItem(
                id=uuid4(),
                store_id=main.id,
                item_id=item.id,
                quantity_on_hand=item.stock_quantity,
                reserved_quantity=Decimal(0),
                reorder_level=item.reorder_level or Decimal(0),
                minimum_stock_level=item.minimum_stock_level or Decimal(0),
                maximum_stock_level=item.maximum_stock_level or Decimal(0),
                location=main.location or item.storage_location,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create(balance)

    def _get_store_for_update(self, store_id: str | None, actor: User) -> InventoryStore:
        store = self.repository.get_store(store_id, for_update=True) if store_id else self._ensure_default_stores(actor)
        if not store or not store.is_active:
            raise AppException(404, "store_not_found", "Inventory store not found")
        self._ensure_branch_scope(store, actor)
        return store

    def _get_or_create_balance(self, store: InventoryStore, item: InventoryItem, actor: User, *, for_update: bool = True) -> InventoryStoreItem:
        balance = self.repository.get_store_balance(store.id, item.id, for_update=for_update)
        if balance:
            return balance
        balance = InventoryStoreItem(
            id=uuid4(),
            store_id=store.id,
            item_id=item.id,
            quantity_on_hand=Decimal(0),
            reserved_quantity=Decimal(0),
            reorder_level=item.reorder_level or Decimal(0),
            minimum_stock_level=item.minimum_stock_level or Decimal(0),
            maximum_stock_level=item.maximum_stock_level or Decimal(0),
            location=store.location or item.storage_location,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(balance)
        return balance

    def _change_store_stock(self, *, store: InventoryStore, item: InventoryItem, delta: Decimal, actor: User, movement_type: str, reference_type: str, reference_id: str | None, batch: StockBatch | None = None, note: str | None = None, unit_cost: Decimal | None = None):
        balance = self._get_or_create_balance(store, item, actor, for_update=True)
        stock_before = Decimal(balance.quantity_on_hand)
        stock_after = stock_before + Decimal(delta)
        if stock_after < 0:
            raise AppException(409, "store_stock_conflict", f"{store.name} stock for {item.name} would go below zero")
        balance.quantity_on_hand = stock_after
        balance.updated_by = actor.id
        item.stock_quantity = Decimal(item.stock_quantity or 0) + Decimal(delta)
        item.stock_value = max(Decimal(0), Decimal(item.stock_value or 0) + (unit_cost or Decimal(0)) * Decimal(delta))
        item.updated_by = actor.id
        transaction = InventoryStockTransaction(
            id=uuid4(),
            item_id=item.id,
            batch_id=batch.id if batch else None,
            store_id=store.id,
            transaction_type=movement_type,
            reference_type=reference_type,
            reference_id=uuid4() if reference_id is None else reference_id,
            quantity_change=Decimal(delta),
            stock_before=stock_before,
            stock_after=stock_after,
            note=self._normalize_text(note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(transaction)
        return transaction

    def _change_item_stock(self, item: InventoryItem, delta: Decimal, actor: User, movement_type: str, reference_type: str, reference_id: str | None, batch: StockBatch | None = None, note: str | None = None, unit_cost: Decimal | None = None):
        stock_before = Decimal(item.stock_quantity)
        stock_after = stock_before + Decimal(delta)
        if stock_after < 0:
            raise AppException(409, "stock_conflict", f"Stock update would reduce {item.name} below zero")
        item.stock_quantity = stock_after
        item.stock_value = max(Decimal(0), item.stock_value + (unit_cost or Decimal(0)) * Decimal(delta))
        item.updated_by = actor.id
        transaction = InventoryStockTransaction(
            id=uuid4(),
            item_id=item.id,
            batch_id=batch.id if batch else None,
            transaction_type=movement_type,
            reference_type=reference_type,
            reference_id=uuid4() if reference_id is None else reference_id,
            quantity_change=Decimal(delta),
            stock_before=stock_before,
            stock_after=stock_after,
            note=self._normalize_text(note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(transaction)
        return transaction

    def _get_item_for_update(self, item_id: str) -> InventoryItem:
        item = self.repository.get_item(item_id, for_update=True)
        if not item or not item.is_active:
            raise AppException(404, "item_not_found", "Inventory item not found")
        return item

    def _get_batch_for_update(self, batch_id: str) -> StockBatch:
        batch = self.repository.get_stock_batch(batch_id, for_update=True)
        if not batch or not batch.is_active:
            raise AppException(404, "batch_not_found", "Stock batch not found")
        return batch

    def _get_item_batch_for_issue(self, item: InventoryItem, batch_id: str | None = None, store_id: str | None = None) -> StockBatch | None:
        if batch_id:
            batch = self._get_batch_for_update(batch_id)
            if store_id and batch.store_id and str(batch.store_id) != str(store_id):
                raise AppException(409, "batch_store_mismatch", "Batch does not belong to the selected store")
            return batch
        if not item.is_batch_tracked:
            return None
        stmt = select(StockBatch).where(StockBatch.item_id == item.id, StockBatch.quantity > 0, StockBatch.is_active.is_(True))
        if store_id:
            stmt = stmt.where(StockBatch.store_id == store_id)
        stmt = stmt.order_by(StockBatch.expiry_date.asc())
        return self.db.scalar(stmt.with_for_update())

    def _serialize_category(self, category: InventoryCategory) -> InventoryCategoryRead:
        return InventoryCategoryRead(
            id=category.id,
            name=category.name,
            description=category.description,
            parent_id=category.parent_id,
            item_type=category.item_type,
            is_active=category.is_active,
            created_at=category.created_at,
        )

    def _serialize_store(self, store: InventoryStore) -> InventoryStoreRead:
        balances = [balance for balance in store.balances if balance.is_active]
        total_value = Decimal(0)
        low = 0
        for balance in balances:
            item = balance.item
            unit_value = Decimal(item.stock_value or 0) / Decimal(item.stock_quantity or 1) if item and Decimal(item.stock_quantity or 0) > 0 else Decimal(0)
            total_value += Decimal(balance.quantity_on_hand or 0) * unit_value
            if Decimal(balance.quantity_on_hand or 0) <= Decimal(balance.reorder_level or 0):
                low += 1
        return InventoryStoreRead(
            id=store.id,
            code=store.code,
            name=store.name,
            store_type=store.store_type,
            department_id=store.department_id,
            parent_store_id=store.parent_store_id,
            department_name=store.department_name,
            location=store.location,
            allow_sub_store_transfers=store.allow_sub_store_transfers,
            description=store.description,
            is_active=store.is_active,
            current_stock_value=total_value,
            total_items=len(balances),
            low_stock_items=low,
            created_at=store.created_at,
        )

    def _stock_status(self, quantity: Decimal, reorder_level: Decimal) -> str:
        if Decimal(quantity or 0) <= 0:
            return "out_of_stock"
        if Decimal(quantity or 0) <= Decimal(reorder_level or 0):
            return "low_stock"
        return "in_stock"

    def _serialize_balance(self, balance: InventoryStoreItem) -> InventoryStoreBalanceRead:
        item = balance.item
        store = balance.store
        return InventoryStoreBalanceRead(
            id=balance.id,
            store_id=balance.store_id,
            store_name=store.name if store else "",
            store_type=store.store_type if store else "store",
            department_name=store.department_name if store else None,
            item_id=balance.item_id,
            item_name=item.name if item else "",
            item_code=item.item_code if item else None,
            category_name=item.category.name if item and item.category else None,
            supplier_name=item.preferred_supplier.name if item and item.preferred_supplier else None,
            quantity_on_hand=balance.quantity_on_hand,
            reserved_quantity=balance.reserved_quantity,
            available_quantity=Decimal(balance.quantity_on_hand or 0) - Decimal(balance.reserved_quantity or 0),
            reorder_level=balance.reorder_level,
            minimum_stock_level=balance.minimum_stock_level,
            maximum_stock_level=balance.maximum_stock_level,
            location=balance.location,
            stock_status=self._stock_status(balance.quantity_on_hand, balance.reorder_level),
            expiry_status=None,
        )

    def _serialize_item(self, item: InventoryItem) -> InventoryItemRead:
        return InventoryItemRead(
            id=item.id,
            name=item.name,
            item_code=item.item_code,
            barcode=item.barcode,
            category_id=item.category_id,
            supplier_id=item.supplier_id,
            sub_category=item.sub_category,
            item_type=item.item_type,
            unit_of_measurement=item.unit_of_measurement,
            is_batch_tracked=item.is_batch_tracked,
            reorder_level=item.reorder_level,
            minimum_stock_level=item.minimum_stock_level,
            maximum_stock_level=item.maximum_stock_level,
            storage_location=item.storage_location,
            tax_rate=item.tax_rate,
            image_url=item.image_url,
            description=item.description,
            is_active=item.is_active,
            stock_quantity=item.stock_quantity,
            stock_value=item.stock_value,
            category_name=item.category.name if item.category else None,
            supplier_name=item.preferred_supplier.name if item.preferred_supplier else None,
            store_balances=[self._serialize_balance(balance) for balance in item.store_balances if balance.is_active],
            created_at=item.created_at,
        )

    def list_stores(self, page: int = 1, page_size: int = 50, q: str | None = None, include_inactive: bool = False, user: User | None = None):
        if user:
            self._ensure_default_stores(user)
        stmt = self.repository.list_stores(branch_id=user.branch_id if user else None, q=q, include_inactive=include_inactive)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [self._serialize_store(store) for store in items], total

    def create_store(self, payload: InventoryStoreCreate, actor: User, context: dict[str, str | None]):
        parent_id = payload.parent_store_id
        if payload.store_type != "main" and not parent_id:
            main = self._ensure_default_stores(actor)
            parent_id = main.id
        store = InventoryStore(
            id=uuid4(),
            branch_id=actor.branch_id,
            department_id=payload.department_id,
            parent_store_id=parent_id,
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            store_type=payload.store_type,
            department_name=self._normalize_text(payload.department_name),
            location=self._normalize_text(payload.location),
            allow_sub_store_transfers=payload.allow_sub_store_transfers,
            description=self._normalize_text(payload.description),
            is_active=payload.is_active,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(store)
        self._commit_and_log(actor=actor, action="inventory.store.create", entity_type="InventoryStore", entity_id=str(store.id), detail={"name": store.name}, context=context)
        return self._serialize_store(store)

    def update_store(self, entity_id: str, payload: InventoryStoreCreate, actor: User, context: dict[str, str | None]):
        store = self._get_store_for_update(entity_id, actor)
        store.department_id = payload.department_id
        store.parent_store_id = payload.parent_store_id
        store.code = payload.code.strip().upper()
        store.name = payload.name.strip()
        store.store_type = payload.store_type
        store.department_name = self._normalize_text(payload.department_name)
        store.location = self._normalize_text(payload.location)
        store.allow_sub_store_transfers = payload.allow_sub_store_transfers
        store.description = self._normalize_text(payload.description)
        store.is_active = payload.is_active
        store.updated_by = actor.id
        self._commit_and_log(actor=actor, action="inventory.store.update", entity_type="InventoryStore", entity_id=str(store.id), detail={"name": store.name, "active": store.is_active}, context=context)
        return self._serialize_store(store)

    def list_store_balances(self, page: int = 1, page_size: int = 100, q: str | None = None, store_id: str | None = None, item_id: str | None = None, stock_status: str | None = None, user: User | None = None):
        if user:
            self._ensure_default_stores(user)
        stmt = self.repository.list_store_balances(branch_id=user.branch_id if user else None, store_id=store_id, item_id=item_id, q=q, stock_status=stock_status)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [self._serialize_balance(balance) for balance in items], total

    def list_items(self, page: int = 1, page_size: int = 20, q: str | None = None, category_id: str | None = None, supplier_id: str | None = None, low_stock: bool = False, user: User | None = None):
        stmt = self.repository.list_items(branch_id=user.branch_id if user else None, q=q, category_id=category_id, supplier_id=supplier_id, low_stock=low_stock)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [self._serialize_item(item) for item in items], total

    def get_item(self, entity_id: str, user: User | None = None):
        item = self.repository.get_item(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "item_not_found", "Inventory item not found")
        self._ensure_branch_scope(item, user) if user else None
        return self._serialize_item(item)

    def create_item(self, payload: InventoryItemCreate, actor: User, context: dict[str, str | None]):
        item = InventoryItem(
            branch_id=actor.branch_id,
            category_id=payload.category_id,
            supplier_id=payload.supplier_id,
            item_code=self._normalize_text(payload.item_code),
            barcode=self._normalize_text(payload.barcode),
            name=payload.name.strip(),
            sub_category=self._normalize_text(payload.sub_category),
            item_type=payload.item_type,
            unit_of_measurement=payload.unit_of_measurement,
            is_batch_tracked=payload.is_batch_tracked,
            reorder_level=payload.reorder_level,
            minimum_stock_level=payload.minimum_stock_level,
            maximum_stock_level=payload.maximum_stock_level,
            storage_location=self._normalize_text(payload.storage_location),
            tax_rate=payload.tax_rate,
            image_url=self._normalize_text(payload.image_url),
            description=self._normalize_text(payload.description),
            is_active=payload.is_active,
            stock_quantity=Decimal(0),
            stock_value=Decimal(0),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="inventory.item.create", entity_type="InventoryItem", entity_id=str(item.id), detail={"name": item.name}, context=context)
        return self._serialize_item(item)

    def update_item(self, entity_id: str, payload: InventoryItemCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(entity_id)
        item.category_id = payload.category_id
        item.supplier_id = payload.supplier_id
        item.item_code = self._normalize_text(payload.item_code)
        item.barcode = self._normalize_text(payload.barcode)
        item.name = payload.name.strip()
        item.sub_category = self._normalize_text(payload.sub_category)
        item.item_type = payload.item_type
        item.unit_of_measurement = payload.unit_of_measurement
        item.is_batch_tracked = payload.is_batch_tracked
        item.reorder_level = payload.reorder_level
        item.minimum_stock_level = payload.minimum_stock_level
        item.maximum_stock_level = payload.maximum_stock_level
        item.storage_location = self._normalize_text(payload.storage_location)
        item.tax_rate = payload.tax_rate
        item.image_url = self._normalize_text(payload.image_url)
        item.description = self._normalize_text(payload.description)
        item.is_active = payload.is_active
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="inventory.item.update", entity_type="InventoryItem", entity_id=str(item.id), detail={"name": item.name}, context=context)
        return self._serialize_item(item)

    def list_suppliers(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_suppliers(branch_id=user.branch_id if user else None, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [SupplierRead(
            id=supplier.id,
            name=supplier.name,
            contact_person=supplier.contact_person,
            phone=supplier.phone,
            email=supplier.email,
            address=supplier.address,
            tax_number=supplier.tax_number,
            payment_terms=supplier.payment_terms,
            rating=int(supplier.rating) if supplier.rating is not None else None,
            note=supplier.note,
            is_active=supplier.is_active,
            created_at=supplier.created_at,
        ) for supplier in items], total

    def get_supplier(self, entity_id: str):
        supplier = self.repository.get_supplier(entity_id)
        if not supplier or not supplier.is_active:
            raise AppException(404, "supplier_not_found", "Supplier not found")
        return SupplierRead(
            id=supplier.id,
            name=supplier.name,
            contact_person=supplier.contact_person,
            phone=supplier.phone,
            email=supplier.email,
            address=supplier.address,
            tax_number=supplier.tax_number,
            payment_terms=supplier.payment_terms,
            rating=int(supplier.rating) if supplier.rating is not None else None,
            note=supplier.note,
            is_active=supplier.is_active,
            created_at=supplier.created_at,
        )

    def create_supplier(self, payload: SupplierCreate, actor: User, context: dict[str, str | None]):
        supplier = Supplier(
            branch_id=actor.branch_id,
            name=payload.name.strip(),
            contact_person=self._normalize_text(payload.contact_person),
            phone=self._normalize_text(payload.phone),
            email=self._normalize_text(payload.email),
            address=self._normalize_text(payload.address),
            tax_number=self._normalize_text(payload.tax_number),
            payment_terms=self._normalize_text(payload.payment_terms),
            rating=payload.rating,
            note=self._normalize_text(payload.note),
            is_active=payload.is_active,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(supplier)
        self._commit_and_log(actor=actor, action="inventory.supplier.create", entity_type="Supplier", entity_id=str(supplier.id), detail={"name": supplier.name}, context=context)
        return self.get_supplier(str(supplier.id))

    def update_supplier(self, entity_id: str, payload: SupplierCreate, actor: User, context: dict[str, str | None]):
        supplier = self.repository.get_supplier(entity_id)
        if not supplier or not supplier.is_active:
            raise AppException(404, "supplier_not_found", "Supplier not found")
        supplier.name = payload.name.strip()
        supplier.contact_person = self._normalize_text(payload.contact_person)
        supplier.phone = self._normalize_text(payload.phone)
        supplier.email = self._normalize_text(payload.email)
        supplier.address = self._normalize_text(payload.address)
        supplier.tax_number = self._normalize_text(payload.tax_number)
        supplier.payment_terms = self._normalize_text(payload.payment_terms)
        supplier.rating = payload.rating
        supplier.note = self._normalize_text(payload.note)
        supplier.is_active = payload.is_active
        supplier.updated_by = actor.id
        self._commit_and_log(actor=actor, action="inventory.supplier.update", entity_type="Supplier", entity_id=str(supplier.id), detail={"name": supplier.name}, context=context)
        return self.get_supplier(entity_id)

    def list_receivings(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_receivings(branch_id=user.branch_id if user else None, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [StockReceivingRead(
            id=record.id,
            item_id=record.item_id,
            store_id=record.store_id,
            supplier_id=record.supplier_id,
            invoice_number=record.invoice_number,
            received_date=record.received_date,
            department=record.department,
            batch_no=record.batch_no,
            expiry_date=record.expiry_date,
            manufacturing_date=record.manufacturing_date,
            quantity=record.quantity,
            unit_cost=record.unit_cost,
            total_cost=record.total_cost,
            note=record.note,
            location=record.department,
            item_name=record.item.name if record.item else None,
            store_name=record.store.name if record.store else None,
            supplier_name=record.supplier.name if record.supplier else None,
            created_at=record.created_at,
        ) for record in items], total

    def create_receiving(self, payload: StockReceivingCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(str(payload.item_id))
        store = self._get_store_for_update(str(payload.store_id) if payload.store_id else None, actor)
        batch = None
        if payload.batch_no and item.is_batch_tracked:
            stmt = select(StockBatch).where(StockBatch.item_id == item.id, StockBatch.store_id == store.id, StockBatch.batch_no == payload.batch_no, StockBatch.is_active.is_(True)).with_for_update()
            batch = self.db.scalar(stmt)
            if batch:
                batch.quantity += payload.quantity
                batch.unit_cost = payload.unit_cost
                batch.total_cost = payload.total_cost
                batch.location = self._normalize_text(payload.department)
                batch.expiry_date = payload.expiry_date
                batch.manufacturing_date = payload.manufacturing_date
            else:
                batch = StockBatch(
                    id=uuid4(),
                    item_id=item.id,
                    store_id=store.id,
                    batch_no=self._normalize_text(payload.batch_no),
                    expiry_date=payload.expiry_date,
                    manufacturing_date=payload.manufacturing_date,
                    quantity=payload.quantity,
                    location=self._normalize_text(payload.department),
                    unit_cost=payload.unit_cost,
                    total_cost=payload.total_cost,
                    notes=self._normalize_text(payload.note),
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.repository.create(batch)
        elif not item.is_batch_tracked:
            batch = None
        receiving = StockReceiving(
            id=uuid4(),
            item_id=item.id,
            store_id=store.id,
            supplier_id=payload.supplier_id,
            invoice_number=self._normalize_text(payload.invoice_number),
            received_date=payload.received_date,
            department=self._normalize_text(payload.department),
            batch_no=self._normalize_text(payload.batch_no),
            expiry_date=payload.expiry_date,
            manufacturing_date=payload.manufacturing_date,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            total_cost=payload.total_cost,
            note=self._normalize_text(payload.note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(receiving)
        self._change_store_stock(store=store, item=item, delta=payload.quantity, actor=actor, movement_type="receive", reference_type="receiving", reference_id=str(receiving.id), batch=batch, note=payload.note, unit_cost=payload.unit_cost)
        self._commit_and_log(actor=actor, action="inventory.receive.create", entity_type="StockReceiving", entity_id=str(receiving.id), detail={"item": item.name, "quantity": str(payload.quantity)}, context=context)
        return StockReceivingRead(
            id=receiving.id,
            item_id=receiving.item_id,
            store_id=receiving.store_id,
            supplier_id=receiving.supplier_id,
            invoice_number=receiving.invoice_number,
            received_date=receiving.received_date,
            department=receiving.department,
            batch_no=receiving.batch_no,
            expiry_date=receiving.expiry_date,
            manufacturing_date=receiving.manufacturing_date,
            quantity=receiving.quantity,
            unit_cost=receiving.unit_cost,
            total_cost=receiving.total_cost,
            note=receiving.note,
            location=receiving.department,
            item_name=item.name,
            store_name=store.name,
            supplier_name=receiving.supplier.name if receiving.supplier else None,
            created_at=receiving.created_at,
        )

    def list_issues(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_issues(branch_id=user.branch_id if user else None, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [StockIssueRead(
            id=issue.id,
            item_id=issue.item_id,
            store_id=issue.store_id,
            batch_id=issue.batch_id,
            department=issue.department,
            requestor=issue.requestor,
            purpose=issue.purpose,
            patient_id=issue.patient_id,
            visit_id=issue.visit_id,
            quantity=issue.quantity,
            issue_date=issue.issue_date,
            note=issue.note,
            item_name=issue.item.name if issue.item else None,
            store_name=issue.store.name if issue.store else None,
            batch_no=issue.batch.batch_no if issue.batch else None,
            created_at=issue.created_at,
        ) for issue in items], total

    def create_issue(self, payload: StockIssueCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(str(payload.item_id))
        store = self._get_store_for_update(str(payload.store_id) if payload.store_id else None, actor)
        balance = self._get_or_create_balance(store, item, actor, for_update=True)
        if payload.quantity > balance.quantity_on_hand:
            raise AppException(409, "stock_unavailable", "Not enough stock to issue")
        batch = self._get_item_batch_for_issue(item, str(payload.batch_id) if payload.batch_id else None, str(store.id))
        if item.is_batch_tracked and batch:
            if payload.quantity > batch.quantity:
                raise AppException(409, "batch_stock_unavailable", "Batch does not have enough stock for issue")
            batch.quantity -= payload.quantity
        issue = StockIssue(
            id=uuid4(),
            item_id=item.id,
            store_id=store.id,
            batch_id=batch.id if batch else None,
            department=self._normalize_text(payload.department),
            requestor=self._normalize_text(payload.requestor),
            purpose=self._normalize_text(payload.purpose),
            patient_id=payload.patient_id,
            visit_id=payload.visit_id,
            quantity=payload.quantity,
            issue_date=payload.issue_date,
            note=self._normalize_text(payload.note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(issue)
        self._change_store_stock(store=store, item=item, delta=-payload.quantity, actor=actor, movement_type="issue", reference_type="issue", reference_id=str(issue.id), batch=batch, note=payload.note)
        self._commit_and_log(actor=actor, action="inventory.issue.create", entity_type="StockIssue", entity_id=str(issue.id), detail={"item": item.name, "quantity": str(payload.quantity)}, context=context)
        return StockIssueRead(
            id=issue.id,
            item_id=issue.item_id,
            store_id=issue.store_id,
            batch_id=issue.batch_id,
            department=issue.department,
            requestor=issue.requestor,
            purpose=issue.purpose,
            patient_id=issue.patient_id,
            visit_id=issue.visit_id,
            quantity=issue.quantity,
            issue_date=issue.issue_date,
            note=issue.note,
            item_name=item.name,
            store_name=store.name,
            batch_no=batch.batch_no if batch else None,
            created_at=issue.created_at,
        )

    def list_transfers(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_transfers(branch_id=user.branch_id if user else None, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [StockTransferRead(
            id=transfer.id,
            item_id=transfer.item_id,
            batch_id=transfer.batch_id,
            source_store_id=transfer.source_store_id,
            destination_store_id=transfer.destination_store_id,
            source_location=transfer.source_location,
            destination_location=transfer.destination_location,
            quantity=transfer.quantity,
            requested_quantity=transfer.requested_quantity,
            approved_quantity=transfer.approved_quantity,
            issued_quantity=transfer.issued_quantity,
            received_quantity=transfer.received_quantity,
            transfer_date=transfer.transfer_date,
            status=transfer.status,
            note=transfer.note,
            item_name=transfer.item.name if transfer.item else None,
            batch_no=transfer.batch.batch_no if transfer.batch else None,
            source_store_name=transfer.source_store.name if transfer.source_store else None,
            destination_store_name=transfer.destination_store.name if transfer.destination_store else None,
            requested_by_name=transfer.requested_by_user.full_name if transfer.requested_by_user else None,
            approved_by_name=transfer.approved_by_user.full_name if transfer.approved_by_user else None,
            issued_by_name=transfer.issued_by_user.full_name if transfer.issued_by_user else None,
            received_by_name=transfer.received_by_user.full_name if transfer.received_by_user else None,
            created_at=transfer.created_at,
        ) for transfer in items], total

    def create_transfer(self, payload: StockTransferCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(str(payload.item_id))
        source_store = self._get_store_for_update(str(payload.source_store_id) if payload.source_store_id else None, actor)
        destination_store = self._get_store_for_update(str(payload.destination_store_id) if payload.destination_store_id else None, actor)
        source_balance = self._get_or_create_balance(source_store, item, actor, for_update=True)
        transfer_quantity = payload.issued_quantity or payload.quantity
        batch = self._get_item_batch_for_issue(item, str(payload.batch_id) if payload.batch_id else None, str(source_store.id))
        if transfer_quantity > source_balance.quantity_on_hand:
            raise AppException(409, "stock_unavailable", "Not enough stock to transfer")
        if batch and transfer_quantity > batch.quantity:
            raise AppException(409, "batch_stock_unavailable", "Batch does not have enough stock to transfer")
        if batch:
            batch.quantity -= transfer_quantity
            new_batch = StockBatch(
                id=uuid4(),
                item_id=item.id,
                store_id=destination_store.id,
                batch_no=batch.batch_no,
                expiry_date=batch.expiry_date,
                manufacturing_date=batch.manufacturing_date,
                quantity=transfer_quantity,
                location=destination_store.location or self._normalize_text(payload.destination_location),
                unit_cost=batch.unit_cost,
                total_cost=batch.unit_cost * transfer_quantity,
                notes=self._normalize_text(payload.note),
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create(new_batch)
        transfer = StockTransfer(
            id=uuid4(),
            item_id=item.id,
            batch_id=batch.id if batch else None,
            source_store_id=source_store.id,
            destination_store_id=destination_store.id,
            source_location=self._normalize_text(payload.source_location) or source_store.name,
            destination_location=self._normalize_text(payload.destination_location) or destination_store.name,
            quantity=transfer_quantity,
            requested_quantity=payload.requested_quantity or payload.quantity,
            approved_quantity=payload.approved_quantity or transfer_quantity,
            issued_quantity=payload.issued_quantity or transfer_quantity,
            received_quantity=payload.received_quantity or transfer_quantity,
            transfer_date=payload.transfer_date,
            status=self._normalize_text(payload.status) or "received",
            note=self._normalize_text(payload.note),
            requested_by=actor.id,
            approved_by=actor.id,
            issued_by=actor.id,
            received_by=actor.id,
            approved_at=datetime.now(UTC),
            issued_at=datetime.now(UTC),
            received_at=datetime.now(UTC),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(transfer)
        self._change_store_stock(store=source_store, item=item, delta=-transfer_quantity, actor=actor, movement_type="transfer_out", reference_type="transfer", reference_id=str(transfer.id), batch=batch, note=payload.note)
        self._change_store_stock(store=destination_store, item=item, delta=transfer_quantity, actor=actor, movement_type="transfer_in", reference_type="transfer", reference_id=str(transfer.id), batch=batch, note=payload.note)
        self._commit_and_log(actor=actor, action="inventory.transfer.create", entity_type="StockTransfer", entity_id=str(transfer.id), detail={"item": item.name, "quantity": str(payload.quantity)}, context=context)
        return StockTransferRead(
            id=transfer.id,
            item_id=transfer.item_id,
            batch_id=transfer.batch_id,
            source_store_id=transfer.source_store_id,
            destination_store_id=transfer.destination_store_id,
            source_location=transfer.source_location,
            destination_location=transfer.destination_location,
            quantity=transfer.quantity,
            requested_quantity=transfer.requested_quantity,
            approved_quantity=transfer.approved_quantity,
            issued_quantity=transfer.issued_quantity,
            received_quantity=transfer.received_quantity,
            transfer_date=transfer.transfer_date,
            status=transfer.status,
            note=transfer.note,
            item_name=item.name,
            batch_no=batch.batch_no if batch else None,
            source_store_name=source_store.name,
            destination_store_name=destination_store.name,
            requested_by_name=actor.full_name,
            approved_by_name=actor.full_name,
            issued_by_name=actor.full_name,
            received_by_name=actor.full_name,
            created_at=transfer.created_at,
        )

    def list_adjustments(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = select(StockAdjustment).options(joinedload(StockAdjustment.item), joinedload(StockAdjustment.batch), joinedload(StockAdjustment.store)).where(StockAdjustment.is_active.is_(True))
        if user and user.branch_id:
            stmt = stmt.where(StockAdjustment.item.has(InventoryItem.branch_id == user.branch_id))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(func.coalesce(StockAdjustment.reason, "")).like(pattern))
        items, total = self._paginate(stmt.order_by(StockAdjustment.created_at.desc()), page=page, page_size=page_size)
        return [StockAdjustmentRead(
            id=adjustment.id,
            item_id=adjustment.item_id,
            batch_id=adjustment.batch_id,
            store_id=adjustment.store_id,
            adjustment_type=adjustment.adjustment_type,
            quantity_change=adjustment.quantity_change,
            reason=adjustment.reason,
            note=adjustment.note,
            status=adjustment.status,
            created_at=adjustment.created_at,
            item_name=adjustment.item.name if adjustment.item else None,
            batch_no=adjustment.batch.batch_no if adjustment.batch else None,
            store_name=adjustment.store.name if adjustment.store else None,
        ) for adjustment in items], total

    def create_adjustment(self, payload: StockAdjustmentCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(str(payload.item_id))
        store = self._get_store_for_update(str(payload.store_id) if payload.store_id else None, actor)
        balance = self._get_or_create_balance(store, item, actor, for_update=True)
        batch = self._get_batch_for_update(str(payload.batch_id)) if payload.batch_id else None
        if payload.adjustment_type.lower() == "deduction" and payload.quantity_change > balance.quantity_on_hand:
            raise AppException(409, "stock_unavailable", "Not enough stock for adjustment")
        if batch and payload.adjustment_type.lower() == "deduction" and payload.quantity_change > batch.quantity:
            raise AppException(409, "batch_stock_unavailable", "Batch stock is insufficient for adjustment")
        delta = payload.quantity_change if payload.adjustment_type.lower() in ["addition", "restock"] else -payload.quantity_change
        if batch:
            batch.quantity += delta
        adjustment = StockAdjustment(
            id=uuid4(),
            item_id=item.id,
            batch_id=batch.id if batch else None,
            store_id=store.id,
            adjustment_type=payload.adjustment_type,
            quantity_change=payload.quantity_change,
            reason=self._normalize_text(payload.reason),
            note=self._normalize_text(payload.note),
            status=payload.status,
            approved_by=actor.id if payload.status in {"posted", "approved"} else None,
            created_by=actor.id,
            updated_by=actor.id,
            created_at=payload.created_at,
        )
        self.repository.create(adjustment)
        if payload.status in {"posted", "approved"}:
            self._change_store_stock(store=store, item=item, delta=delta, actor=actor, movement_type="adjustment", reference_type="adjustment", reference_id=str(adjustment.id), batch=batch, note=payload.reason)
        self._commit_and_log(actor=actor, action="inventory.adjustment.create", entity_type="StockAdjustment", entity_id=str(adjustment.id), detail={"item": item.name, "quantity": str(delta)}, context=context)
        return StockAdjustmentRead(
            id=adjustment.id,
            item_id=adjustment.item_id,
            batch_id=adjustment.batch_id,
            store_id=adjustment.store_id,
            adjustment_type=adjustment.adjustment_type,
            quantity_change=adjustment.quantity_change,
            reason=adjustment.reason,
            note=adjustment.note,
            status=adjustment.status,
            created_at=adjustment.created_at,
            item_name=item.name,
            batch_no=batch.batch_no if batch else None,
            store_name=store.name,
        )

    def list_purchase_requests(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_purchase_requests(branch_id=user.branch_id if user else None, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [PurchaseRequestRead(
            id=req.id,
            item_id=req.item_id,
            supplier_id=req.supplier_id,
            department=req.department,
            requested_quantity=req.requested_quantity,
            priority=req.priority,
            expected_date=req.expected_date,
            status=req.status,
            note=req.note,
            item_name=req.item.name if req.item else None,
            supplier_name=req.supplier.name if req.supplier else None,
            requested_by_name=req.requested_by_user.full_name if req.requested_by_user else None,
            approved_by_name=req.approved_by_user.full_name if req.approved_by_user else None,
            created_at=req.created_at,
        ) for req in items], total

    def create_purchase_request(self, payload: PurchaseRequestCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(str(payload.item_id))
        request = PurchaseRequest(
            id=uuid4(),
            item_id=item.id,
            supplier_id=payload.supplier_id,
            department=self._normalize_text(payload.department),
            requested_quantity=payload.requested_quantity,
            priority=self._normalize_text(payload.priority),
            expected_date=payload.expected_date,
            status=self._normalize_text(payload.status),
            note=self._normalize_text(payload.note),
            requested_by=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(request)
        self._commit_and_log(actor=actor, action="inventory.purchase-request.create", entity_type="PurchaseRequest", entity_id=str(request.id), detail={"item": item.name, "quantity": str(payload.requested_quantity)}, context=context)
        return PurchaseRequestRead(
            id=request.id,
            item_id=request.item_id,
            supplier_id=request.supplier_id,
            department=request.department,
            requested_quantity=request.requested_quantity,
            priority=request.priority,
            expected_date=request.expected_date,
            status=request.status,
            note=request.note,
            item_name=item.name,
            supplier_name=request.supplier.name if request.supplier else None,
            requested_by_name=actor.full_name,
            approved_by_name=None,
            created_at=request.created_at,
        )

    def update_purchase_request(self, entity_id: str, payload: PurchaseRequestCreate, actor: User, context: dict[str, str | None]):
        request = self.repository.get_purchase_request(entity_id)
        if not request or not request.is_active:
            raise AppException(404, "purchase_request_not_found", "Purchase request not found")
        request.supplier_id = payload.supplier_id
        request.department = self._normalize_text(payload.department)
        request.requested_quantity = payload.requested_quantity
        request.priority = self._normalize_text(payload.priority)
        request.expected_date = payload.expected_date
        request.status = self._normalize_text(payload.status)
        request.note = self._normalize_text(payload.note)
        request.updated_by = actor.id
        if payload.status == "approved":
            request.approved_by = actor.id
        self._commit_and_log(actor=actor, action="inventory.purchase-request.update", entity_type="PurchaseRequest", entity_id=str(request.id), detail={"status": request.status}, context=context)
        return PurchaseRequestRead(
            id=request.id,
            item_id=request.item_id,
            supplier_id=request.supplier_id,
            department=request.department,
            requested_quantity=request.requested_quantity,
            priority=request.priority,
            expected_date=request.expected_date,
            status=request.status,
            note=request.note,
            item_name=request.item.name if request.item else None,
            supplier_name=request.supplier.name if request.supplier else None,
            requested_by_name=request.requested_by_user.full_name if request.requested_by_user else None,
            approved_by_name=request.approved_by_user.full_name if request.approved_by_user else None,
            created_at=request.created_at,
        )

    def _serialize_requisition(self, req: InventoryRequisition) -> InventoryRequisitionRead:
        return InventoryRequisitionRead(
            id=req.id,
            item_id=req.item_id,
            source_store_id=req.source_store_id,
            destination_store_id=req.destination_store_id,
            department=req.department,
            requested_quantity=req.requested_quantity,
            approved_quantity=req.approved_quantity,
            issued_quantity=req.issued_quantity,
            priority=req.priority,
            required_date=req.required_date,
            reason=req.reason,
            status=req.status,
            remarks=req.remarks,
            item_name=req.item.name if req.item else None,
            source_store_name=req.source_store.name if req.source_store else None,
            destination_store_name=req.destination_store.name if req.destination_store else None,
            requested_by_name=req.requested_by_user.full_name if req.requested_by_user else None,
            approved_by_name=req.approved_by_user.full_name if req.approved_by_user else None,
            rejected_by_name=req.rejected_by_user.full_name if req.rejected_by_user else None,
            issued_by_name=req.issued_by_user.full_name if req.issued_by_user else None,
            created_at=req.created_at,
        )

    def list_requisitions(self, page: int = 1, page_size: int = 50, q: str | None = None, store_id: str | None = None, status: str | None = None, user: User | None = None):
        if user:
            self._ensure_default_stores(user)
        stmt = self.repository.list_requisitions(branch_id=user.branch_id if user else None, q=q, store_id=store_id, status=status)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [self._serialize_requisition(req) for req in items], total

    def create_requisition(self, payload: InventoryRequisitionCreate, actor: User, context: dict[str, str | None]):
        item = self._get_item_for_update(str(payload.item_id))
        destination = self._get_store_for_update(str(payload.destination_store_id), actor)
        source = self._get_store_for_update(str(payload.source_store_id) if payload.source_store_id else None, actor)
        req = InventoryRequisition(
            id=uuid4(),
            item_id=item.id,
            source_store_id=source.id,
            destination_store_id=destination.id,
            department=self._normalize_text(payload.department) or destination.department_name,
            requested_quantity=payload.requested_quantity,
            approved_quantity=payload.approved_quantity or Decimal(0),
            issued_quantity=payload.issued_quantity or Decimal(0),
            priority=self._normalize_text(payload.priority) or "normal",
            required_date=payload.required_date,
            reason=self._normalize_text(payload.reason),
            status=self._normalize_text(payload.status) or "requested",
            remarks=self._normalize_text(payload.remarks),
            requested_by=actor.id,
            approved_by=actor.id if payload.status in {"approved", "partially_approved", "issued"} else None,
            issued_by=actor.id if payload.status == "issued" else None,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(req)
        if req.status == "issued" and req.issued_quantity > 0:
            self.create_transfer(
                StockTransferCreate(
                    item_id=item.id,
                    source_store_id=source.id,
                    destination_store_id=destination.id,
                    quantity=req.issued_quantity,
                    requested_quantity=req.requested_quantity,
                    approved_quantity=req.approved_quantity or req.issued_quantity,
                    issued_quantity=req.issued_quantity,
                    received_quantity=req.issued_quantity,
                    transfer_date=date.today(),
                    status="received",
                    note=f"Issued against requisition {req.id}",
                ),
                actor,
                context,
            )
        self._commit_and_log(actor=actor, action="inventory.requisition.create", entity_type="InventoryRequisition", entity_id=str(req.id), detail={"item": item.name, "status": req.status}, context=context)
        return self._serialize_requisition(req)

    def update_requisition(self, entity_id: str, payload: InventoryRequisitionCreate, actor: User, context: dict[str, str | None]):
        req = self.repository.get_requisition(entity_id, for_update=True)
        if not req or not req.is_active:
            raise AppException(404, "requisition_not_found", "Inventory requisition not found")
        req.source_store_id = payload.source_store_id or req.source_store_id
        req.destination_store_id = payload.destination_store_id
        req.department = self._normalize_text(payload.department)
        req.requested_quantity = payload.requested_quantity
        req.approved_quantity = payload.approved_quantity or Decimal(0)
        req.issued_quantity = payload.issued_quantity or Decimal(0)
        req.priority = self._normalize_text(payload.priority) or "normal"
        req.required_date = payload.required_date
        req.reason = self._normalize_text(payload.reason)
        req.status = self._normalize_text(payload.status) or req.status
        req.remarks = self._normalize_text(payload.remarks)
        req.updated_by = actor.id
        if req.status in {"approved", "partially_approved", "issued"}:
            req.approved_by = actor.id
        if req.status == "rejected":
            req.rejected_by = actor.id
        if req.status == "issued":
            req.issued_by = actor.id
        self._commit_and_log(actor=actor, action="inventory.requisition.update", entity_type="InventoryRequisition", entity_id=str(req.id), detail={"status": req.status}, context=context)
        return self._serialize_requisition(req)

    def list_reagents(self, page: int = 1, page_size: int = 20, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_reagents(branch_id=user.branch_id if user else None, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [ReagentRead(
            id=reagent.id,
            reagent_code=reagent.reagent_code,
            name=reagent.name,
            category=reagent.category,
            test_mapping=reagent.test_mapping,
            analyzer_mapping=reagent.analyzer_mapping,
            manufacturer=reagent.manufacturer,
            supplier_id=reagent.supplier_id,
            storage_condition=reagent.storage_condition,
            opening_date=reagent.opening_date,
            opening_balance=reagent.opening_balance,
            opened_balance=reagent.opened_balance,
            closed_balance=reagent.closed_balance,
            stability_days=reagent.stability_days,
            status=reagent.status,
            note=reagent.note,
            supplier_name=reagent.supplier.name if reagent.supplier else None,
            created_at=reagent.created_at,
        ) for reagent in items], total

    def get_reagent(self, entity_id: str):
        reagent = self.repository.get_reagent(entity_id)
        if not reagent or not reagent.is_active:
            raise AppException(404, "reagent_not_found", "Reagent not found")
        return ReagentRead(
            id=reagent.id,
            reagent_code=reagent.reagent_code,
            name=reagent.name,
            category=reagent.category,
            test_mapping=reagent.test_mapping,
            analyzer_mapping=reagent.analyzer_mapping,
            manufacturer=reagent.manufacturer,
            supplier_id=reagent.supplier_id,
            storage_condition=reagent.storage_condition,
            opening_date=reagent.opening_date,
            opening_balance=reagent.opening_balance,
            opened_balance=reagent.opened_balance,
            closed_balance=reagent.closed_balance,
            stability_days=reagent.stability_days,
            status=reagent.status,
            note=reagent.note,
            supplier_name=reagent.supplier.name if reagent.supplier else None,
            created_at=reagent.created_at,
        )

    def create_reagent(self, payload: ReagentCreate, actor: User, context: dict[str, str | None]):
        reagent = Reagent(
            id=uuid4(),
            branch_id=actor.branch_id,
            reagent_code=payload.reagent_code.strip(),
            name=payload.name.strip(),
            category=payload.category,
            test_mapping=self._normalize_text(payload.test_mapping),
            analyzer_mapping=self._normalize_text(payload.analyzer_mapping),
            manufacturer=self._normalize_text(payload.manufacturer),
            supplier_id=payload.supplier_id,
            storage_condition=self._normalize_text(payload.storage_condition),
            opening_date=payload.opening_date,
            opening_balance=payload.opening_balance,
            opened_balance=payload.opened_balance or Decimal(0),
            closed_balance=payload.closed_balance or Decimal(0),
            stability_days=payload.stability_days,
            status=payload.status,
            note=self._normalize_text(payload.note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(reagent)
        self._commit_and_log(actor=actor, action="inventory.reagent.create", entity_type="Reagent", entity_id=str(reagent.id), detail={"name": reagent.name}, context=context)
        return self.get_reagent(str(reagent.id))

    def update_reagent(self, entity_id: str, payload: ReagentCreate, actor: User, context: dict[str, str | None]):
        reagent = self.repository.get_reagent(entity_id, for_update=True)
        if not reagent or not reagent.is_active:
            raise AppException(404, "reagent_not_found", "Reagent not found")
        reagent.reagent_code = payload.reagent_code.strip()
        reagent.name = payload.name.strip()
        reagent.category = payload.category
        reagent.test_mapping = self._normalize_text(payload.test_mapping)
        reagent.analyzer_mapping = self._normalize_text(payload.analyzer_mapping)
        reagent.manufacturer = self._normalize_text(payload.manufacturer)
        reagent.supplier_id = payload.supplier_id
        reagent.storage_condition = self._normalize_text(payload.storage_condition)
        reagent.opening_date = payload.opening_date
        reagent.opening_balance = payload.opening_balance
        reagent.opened_balance = payload.opened_balance or Decimal(0)
        reagent.closed_balance = payload.closed_balance or Decimal(0)
        reagent.stability_days = payload.stability_days
        reagent.status = payload.status
        reagent.note = self._normalize_text(payload.note)
        reagent.updated_by = actor.id
        self._commit_and_log(actor=actor, action="inventory.reagent.update", entity_type="Reagent", entity_id=str(reagent.id), detail={"name": reagent.name}, context=context)
        return self.get_reagent(entity_id)

    def list_reagent_batches(self, page: int = 1, page_size: int = 20, reagent_id: str | None = None, q: str | None = None, user: User | None = None):
        stmt = self.repository.list_reagent_batches(reagent_id=reagent_id, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [ReagentBatchRead(
            id=batch.id,
            reagent_id=batch.reagent_id,
            batch_no=batch.batch_no,
            lot_number=batch.lot_number,
            expiry_date=batch.expiry_date,
            manufacturing_date=batch.manufacturing_date,
            quantity_received=batch.quantity_received,
            quantity_available=batch.quantity_available,
            quantity_opened=batch.quantity_opened,
            opened_at=batch.opened_at,
            stability_days=batch.stability_days,
            status=batch.status,
            supplier_id=batch.supplier_id,
            note=batch.note,
            reagent_name=batch.reagent.name if batch.reagent else None,
            supplier_name=batch.supplier.name if batch.supplier else None,
            created_at=batch.created_at,
        ) for batch in items], total

    def create_reagent_batch(self, payload: ReagentBatchCreate, actor: User, context: dict[str, str | None]):
        reagent = self.repository.get_reagent(payload.reagent_id, for_update=True)
        if not reagent or not reagent.is_active:
            raise AppException(404, "reagent_not_found", "Reagent not found")
        batch = ReagentBatch(
            id=uuid4(),
            reagent_id=reagent.id,
            batch_no=self._normalize_text(payload.batch_no),
            lot_number=self._normalize_text(payload.lot_number),
            expiry_date=payload.expiry_date,
            manufacturing_date=payload.manufacturing_date,
            quantity_received=payload.quantity_received,
            quantity_available=payload.quantity_available,
            quantity_opened=payload.quantity_opened,
            opened_at=payload.opened_at,
            stability_days=payload.stability_days,
            status=payload.status,
            supplier_id=payload.supplier_id,
            note=self._normalize_text(payload.note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(batch)
        self._commit_and_log(actor=actor, action="inventory.reagent.batch.create", entity_type="ReagentBatch", entity_id=str(batch.id), detail={"reagent": reagent.name}, context=context)
        return ReagentBatchRead(
            id=batch.id,
            reagent_id=batch.reagent_id,
            batch_no=batch.batch_no,
            lot_number=batch.lot_number,
            expiry_date=batch.expiry_date,
            manufacturing_date=batch.manufacturing_date,
            quantity_received=batch.quantity_received,
            quantity_available=batch.quantity_available,
            quantity_opened=batch.quantity_opened,
            opened_at=batch.opened_at,
            stability_days=batch.stability_days,
            status=batch.status,
            supplier_id=batch.supplier_id,
            note=batch.note,
            reagent_name=reagent.name,
            supplier_name=batch.supplier.name if batch.supplier else None,
            created_at=batch.created_at,
        )

    def list_reagent_usage(self, page: int = 1, page_size: int = 20, reagent_id: str | None = None, q: str | None = None):
        stmt = self.repository.list_reagent_usage(reagent_id=reagent_id, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [ReagentUsageRead(
            id=usage.id,
            reagent_id=usage.reagent_id,
            batch_id=usage.batch_id,
            analyzer_name=usage.analyzer_name,
            test_name=usage.test_name,
            quantity_used=usage.quantity_used,
            reagent_cost=usage.reagent_cost,
            used_at=usage.used_at,
            note=usage.note,
            reagent_name=usage.reagent.name if usage.reagent else None,
            batch_no=usage.batch.batch_no if usage.batch else None,
            created_by_name=usage.created_by_user.full_name if usage.created_by_user else None,
            created_at=usage.created_at,
        ) for usage in items], total

    def create_reagent_usage(self, payload: ReagentUsageCreate, actor: User, context: dict[str, str | None]):
        reagent = self.repository.get_reagent(payload.reagent_id, for_update=True)
        if not reagent or not reagent.is_active:
            raise AppException(404, "reagent_not_found", "Reagent not found")
        batch = None
        if payload.batch_id:
            batch = self.repository.get_reagent_batch(str(payload.batch_id), for_update=True)
            if not batch or not batch.is_active:
                raise AppException(404, "batch_not_found", "Reagent batch not found")
            if payload.quantity_used > batch.quantity_available:
                raise AppException(409, "batch_stock_unavailable", "Not enough reagent available in selected batch")
            batch.quantity_available -= payload.quantity_used
            if batch.quantity_opened is not None:
                batch.quantity_opened = max(Decimal(0), (batch.quantity_opened or Decimal(0)) - payload.quantity_used)
        usage = ReagentUsage(
            id=uuid4(),
            reagent_id=reagent.id,
            batch_id=batch.id if batch else None,
            analyzer_name=self._normalize_text(payload.analyzer_name),
            test_name=payload.test_name.strip(),
            quantity_used=payload.quantity_used,
            reagent_cost=payload.reagent_cost,
            used_at=payload.used_at,
            note=self._normalize_text(payload.note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(usage)
        self._commit_and_log(actor=actor, action="inventory.reagent.usage.create", entity_type="ReagentUsage", entity_id=str(usage.id), detail={"reagent": reagent.name, "quantity": str(payload.quantity_used)}, context=context)
        return ReagentUsageRead(
            id=usage.id,
            reagent_id=usage.reagent_id,
            batch_id=usage.batch_id,
            analyzer_name=usage.analyzer_name,
            test_name=usage.test_name,
            quantity_used=usage.quantity_used,
            reagent_cost=usage.reagent_cost,
            used_at=usage.used_at,
            note=usage.note,
            reagent_name=reagent.name,
            batch_no=batch.batch_no if batch else None,
            created_by_name=actor.full_name,
            created_at=usage.created_at,
        )

    def list_reagent_wastage(self, page: int = 1, page_size: int = 20, reagent_id: str | None = None, q: str | None = None):
        stmt = self.repository.list_reagent_wastage(reagent_id=reagent_id, q=q)
        items, total = self._paginate(stmt, page=page, page_size=page_size)
        return [ReagentWastageRead(
            id=wastage.id,
            reagent_id=wastage.reagent_id,
            batch_id=wastage.batch_id,
            wasted_quantity=wastage.wasted_quantity,
            reason=wastage.reason,
            status=wastage.status,
            recorded_at=wastage.recorded_at,
            note=wastage.note,
            reagent_name=wastage.reagent.name if wastage.reagent else None,
            batch_no=wastage.batch.batch_no if wastage.batch else None,
            created_by_name=wastage.created_by_user.full_name if wastage.created_by_user else None,
            created_at=wastage.created_at,
        ) for wastage in items], total

    def create_reagent_wastage(self, payload: ReagentWastageCreate, actor: User, context: dict[str, str | None]):
        reagent = self.repository.get_reagent(payload.reagent_id, for_update=True)
        if not reagent or not reagent.is_active:
            raise AppException(404, "reagent_not_found", "Reagent not found")
        batch = None
        if payload.batch_id:
            batch = self.repository.get_reagent_batch(str(payload.batch_id), for_update=True)
            if not batch or not batch.is_active:
                raise AppException(404, "batch_not_found", "Reagent batch not found")
            if payload.wasted_quantity > batch.quantity_available:
                raise AppException(409, "batch_stock_unavailable", "Not enough reagent available for wastage")
            batch.quantity_available -= payload.wasted_quantity
            batch.status = payload.status
        wastage = ReagentWastage(
            id=uuid4(),
            reagent_id=reagent.id,
            batch_id=batch.id if batch else None,
            wasted_quantity=payload.wasted_quantity,
            reason=self._normalize_text(payload.reason),
            status=payload.status,
            recorded_at=payload.recorded_at,
            note=self._normalize_text(payload.note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(wastage)
        self._commit_and_log(actor=actor, action="inventory.reagent.wastage.create", entity_type="ReagentWastage", entity_id=str(wastage.id), detail={"reagent": reagent.name, "quantity": str(payload.wasted_quantity)}, context=context)
        return ReagentWastageRead(
            id=wastage.id,
            reagent_id=wastage.reagent_id,
            batch_id=wastage.batch_id,
            wasted_quantity=wastage.wasted_quantity,
            reason=wastage.reason,
            status=wastage.status,
            recorded_at=wastage.recorded_at,
            note=wastage.note,
            reagent_name=reagent.name,
            batch_no=batch.batch_no if batch else None,
            created_by_name=actor.full_name,
            created_at=wastage.created_at,
        )

    def get_dashboard_summary(self, user: User | None = None):
        branch_id = user.branch_id if user else None
        if user:
            self._ensure_default_stores(user)
        stmt = select(func.coalesce(func.sum(InventoryItem.stock_value), 0)).where(InventoryItem.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        total_stock = Decimal(self.db.scalar(stmt) or 0)

        stmt = select(func.count(InventoryItem.id)).where(InventoryItem.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        total_items = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(InventoryItem.id)).where(InventoryItem.is_active.is_(True), InventoryItem.stock_quantity <= InventoryItem.reorder_level)
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        low_stock = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(InventoryItem.id)).where(InventoryItem.is_active.is_(True), InventoryItem.stock_quantity <= 0)
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        out_of_stock = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(StockBatch.id)).where(StockBatch.is_active.is_(True), StockBatch.expiry_date <= date.today())
        if branch_id:
            stmt = stmt.where(StockBatch.item.has(InventoryItem.branch_id == branch_id))
        near_expiry = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(StockReceiving.id)).where(StockReceiving.received_date >= date.today())
        if branch_id:
            stmt = stmt.where(StockReceiving.item.has(InventoryItem.branch_id == branch_id))
        recent_receivings = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(StockIssue.id)).where(StockIssue.issue_date >= date.today())
        if branch_id:
            stmt = stmt.where(StockIssue.item.has(InventoryItem.branch_id == branch_id))
        recent_issues = int(self.db.scalar(stmt) or 0)

        category_stmt = select(InventoryItem.item_type, func.count(InventoryItem.id)).where(InventoryItem.is_active.is_(True))
        if branch_id:
            category_stmt = category_stmt.where(InventoryItem.branch_id == branch_id)
        category_stmt = category_stmt.group_by(InventoryItem.item_type)
        category_counts = {row[0]: int(row[1]) for row in self.db.execute(category_stmt).all()}
        stores_stmt = select(InventoryStore).where(InventoryStore.is_active.is_(True))
        if branch_id:
            stores_stmt = stores_stmt.where(InventoryStore.branch_id == branch_id)
        stores = list(self.db.scalars(stores_stmt))
        store_stock_value = {store.name: Decimal(0) for store in stores}
        for balance in self.db.scalars(select(InventoryStoreItem).options(joinedload(InventoryStoreItem.store), joinedload(InventoryStoreItem.item)).where(InventoryStoreItem.is_active.is_(True))).all():
            if branch_id and balance.store and balance.store.branch_id != branch_id:
                continue
            unit_value = Decimal(balance.item.stock_value or 0) / Decimal(balance.item.stock_quantity or 1) if balance.item and Decimal(balance.item.stock_quantity or 0) > 0 else Decimal(0)
            store_stock_value[balance.store.name if balance.store else "Store"] = store_stock_value.get(balance.store.name if balance.store else "Store", Decimal(0)) + Decimal(balance.quantity_on_hand or 0) * unit_value

        open_requisitions = int(self.db.scalar(select(func.count(InventoryRequisition.id)).where(InventoryRequisition.status.in_(["draft", "requested", "approved", "partially_approved"]))) or 0)
        open_transfers = int(self.db.scalar(select(func.count(StockTransfer.id)).where(StockTransfer.status.in_(["draft", "requested", "approved", "partially_issued", "issued", "partially_received"]))) or 0)

        return InventoryDashboardSummaryRead(
            total_stock_value=total_stock,
            total_items=total_items,
            low_stock_items=low_stock,
            out_of_stock_items=out_of_stock,
            near_expiry_items=near_expiry,
            recent_receivings=recent_receivings,
            recent_issues=recent_issues,
            category_counts=category_counts,
            total_stores=len(stores),
            open_requisitions=open_requisitions,
            open_transfers=open_transfers,
            store_stock_value=store_stock_value,
        )

    def get_report_summary(self, user: User | None = None):
        branch_id = user.branch_id if user else None
        stmt = select(func.count(InventoryItem.id)).where(InventoryItem.is_active.is_(True), InventoryItem.stock_quantity <= InventoryItem.reorder_level)
        if branch_id:
            stmt = stmt.where(InventoryItem.branch_id == branch_id)
        low_stock_items = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(StockBatch.id)).where(StockBatch.is_active.is_(True), StockBatch.expiry_date <= date.today())
        if branch_id:
            stmt = stmt.where(StockBatch.item.has(InventoryItem.branch_id == branch_id))
        near_expiry_batches = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(StockBatch.id)).where(StockBatch.is_active.is_(True), StockBatch.expiry_date < date.today())
        if branch_id:
            stmt = stmt.where(StockBatch.item.has(InventoryItem.branch_id == branch_id))
        expired_batches = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(ReagentUsage.id)).where(ReagentUsage.used_at >= date.today())
        if branch_id:
            stmt = stmt.where(ReagentUsage.reagent.has(Reagent.branch_id == branch_id))
        reagent_usage_last_7_days = int(self.db.scalar(stmt) or 0)

        stmt = select(func.count(PurchaseRequest.id)).where(PurchaseRequest.status.in_(["requested", "approved", "ordered"]))
        if branch_id:
            stmt = stmt.where(PurchaseRequest.item.has(InventoryItem.branch_id == branch_id))
        purchase_requests_open = int(self.db.scalar(stmt) or 0)
        open_requisitions = int(self.db.scalar(select(func.count(InventoryRequisition.id)).where(InventoryRequisition.status.in_(["draft", "requested", "approved", "partially_approved"]))) or 0)
        open_transfers = int(self.db.scalar(select(func.count(StockTransfer.id)).where(StockTransfer.status.in_(["draft", "requested", "approved", "partially_issued", "issued", "partially_received"]))) or 0)
        adjustment_count = int(self.db.scalar(select(func.count(StockAdjustment.id)).where(StockAdjustment.created_at >= date.today() - timedelta(days=30))) or 0)

        return InventoryReportRead(
            low_stock_items=low_stock_items,
            near_expiry_batches=near_expiry_batches,
            expired_batches=expired_batches,
            reagent_usage_last_7_days=reagent_usage_last_7_days,
            purchase_requests_open=purchase_requests_open,
            open_requisitions=open_requisitions,
            open_transfers=open_transfers,
            adjustment_count=adjustment_count,
        )
