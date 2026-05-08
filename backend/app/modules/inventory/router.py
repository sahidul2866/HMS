from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.inventory.service import InventoryService
from app.schemas.inventory import (
    InventoryDashboardSummaryRead,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryReportRead,
    InventoryRequisitionCreate,
    InventoryRequisitionRead,
    InventoryStoreBalanceRead,
    InventoryStoreCreate,
    InventoryStoreRead,
    PaginatedResponse,
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
    StockAdjustmentCreate,
    StockAdjustmentRead,
    StockIssueCreate,
    StockIssueRead,
    StockReceivingCreate,
    StockReceivingRead,
    StockTransferCreate,
    StockTransferRead,
    SupplierCreate,
    SupplierRead,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/dashboard", response_model=InventoryDashboardSummaryRead, dependencies=[Depends(require_permissions("inventory.view"))])
def get_dashboard_summary(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).get_dashboard_summary(user)


@router.get("/reports", response_model=InventoryReportRead, dependencies=[Depends(require_permissions("inventory.view"))])
def get_report_summary(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).get_report_summary(user)


@router.get("/items", response_model=PaginatedResponse[InventoryItemRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category_id: UUID | None = None,
    supplier_id: UUID | None = None,
    low_stock: bool = False,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_items(page=page, page_size=page_size, q=q, category_id=category_id, supplier_id=supplier_id, low_stock=low_stock, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/stores", response_model=PaginatedResponse[InventoryStoreRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_stores(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    q: str | None = None,
    include_inactive: bool = False,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_stores(page=page, page_size=page_size, q=q, include_inactive=include_inactive, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/stores", response_model=InventoryStoreRead, dependencies=[Depends(require_permissions("inventory.store.manage"))])
def create_store(payload: InventoryStoreCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_store(payload, user, context)


@router.put("/stores/{entity_id}", response_model=InventoryStoreRead, dependencies=[Depends(require_permissions("inventory.store.manage"))])
def update_store(entity_id: UUID, payload: InventoryStoreCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).update_store(str(entity_id), payload, user, context)


@router.get("/stock", response_model=PaginatedResponse[InventoryStoreBalanceRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_store_stock(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    q: str | None = None,
    store_id: UUID | None = None,
    item_id: UUID | None = None,
    stock_status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_store_balances(page=page, page_size=page_size, q=q, store_id=str(store_id) if store_id else None, item_id=str(item_id) if item_id else None, stock_status=stock_status, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/items", response_model=InventoryItemRead, dependencies=[Depends(require_permissions("inventory.item.create"))])
def create_item(payload: InventoryItemCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_item(payload, user, context)


@router.get("/items/{entity_id}", response_model=InventoryItemRead, dependencies=[Depends(require_permissions("inventory.view"))])
def get_item(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).get_item(str(entity_id), user)


@router.put("/items/{entity_id}", response_model=InventoryItemRead, dependencies=[Depends(require_permissions("inventory.item.edit"))])
def update_item(entity_id: UUID, payload: InventoryItemCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).update_item(str(entity_id), payload, user, context)


@router.get("/suppliers", response_model=PaginatedResponse[SupplierRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_suppliers(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/suppliers", response_model=SupplierRead, dependencies=[Depends(require_permissions("inventory.item.create"))])
def create_supplier(payload: SupplierCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_supplier(payload, user, context)


@router.get("/suppliers/{entity_id}", response_model=SupplierRead, dependencies=[Depends(require_permissions("inventory.view"))])
def get_supplier(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).get_supplier(str(entity_id))


@router.put("/suppliers/{entity_id}", response_model=SupplierRead, dependencies=[Depends(require_permissions("inventory.item.edit"))])
def update_supplier(entity_id: UUID, payload: SupplierCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).update_supplier(str(entity_id), payload, user, context)


@router.get("/receivings", response_model=PaginatedResponse[StockReceivingRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_receivings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_receivings(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/receivings", response_model=StockReceivingRead, dependencies=[Depends(require_permissions("inventory.stock.receive"))])
def create_receiving(payload: StockReceivingCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_receiving(payload, user, context)


@router.get("/issues", response_model=PaginatedResponse[StockIssueRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_issues(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/issues", response_model=StockIssueRead, dependencies=[Depends(require_permissions("inventory.stock.issue"))])
def create_issue(payload: StockIssueCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_issue(payload, user, context)


@router.get("/transfers", response_model=PaginatedResponse[StockTransferRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_transfers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_transfers(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/transfers", response_model=StockTransferRead, dependencies=[Depends(require_permissions("inventory.stock.transfer"))])
def create_transfer(payload: StockTransferCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_transfer(payload, user, context)


@router.get("/adjustments", response_model=PaginatedResponse[StockAdjustmentRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_adjustments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_adjustments(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/adjustments", response_model=StockAdjustmentRead, dependencies=[Depends(require_permissions("inventory.stock.adjust"))])
def create_adjustment(payload: StockAdjustmentCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_adjustment(payload, user, context)


@router.get("/purchase-requests", response_model=PaginatedResponse[PurchaseRequestRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_purchase_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_purchase_requests(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/purchase-requests", response_model=PurchaseRequestRead, dependencies=[Depends(require_permissions("inventory.purchase"))])
def create_purchase_request(payload: PurchaseRequestCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_purchase_request(payload, user, context)


@router.put("/purchase-requests/{entity_id}", response_model=PurchaseRequestRead, dependencies=[Depends(require_permissions("inventory.purchase"))])
def update_purchase_request(entity_id: UUID, payload: PurchaseRequestCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).update_purchase_request(str(entity_id), payload, user, context)


@router.get("/requisitions", response_model=PaginatedResponse[InventoryRequisitionRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_requisitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    q: str | None = None,
    store_id: UUID | None = None,
    status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_requisitions(page=page, page_size=page_size, q=q, store_id=str(store_id) if store_id else None, status=status, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/requisitions", response_model=InventoryRequisitionRead, dependencies=[Depends(require_permissions("inventory.requisition.create"))])
def create_requisition(payload: InventoryRequisitionCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_requisition(payload, user, context)


@router.put("/requisitions/{entity_id}", response_model=InventoryRequisitionRead, dependencies=[Depends(require_permissions("inventory.requisition.approve"))])
def update_requisition(entity_id: UUID, payload: InventoryRequisitionCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).update_requisition(str(entity_id), payload, user, context)


@router.get("/reagents", response_model=PaginatedResponse[ReagentRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_reagents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_reagents(page=page, page_size=page_size, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/reagents", response_model=ReagentRead, dependencies=[Depends(require_permissions("inventory.manage"))])
def create_reagent(payload: ReagentCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_reagent(payload, user, context)


@router.get("/reagents/{entity_id}", response_model=ReagentRead, dependencies=[Depends(require_permissions("inventory.view"))])
def get_reagent(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).get_reagent(str(entity_id))


@router.put("/reagents/{entity_id}", response_model=ReagentRead, dependencies=[Depends(require_permissions("inventory.manage"))])
def update_reagent(entity_id: UUID, payload: ReagentCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).update_reagent(str(entity_id), payload, user, context)


@router.get("/reagent-batches", response_model=PaginatedResponse[ReagentBatchRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_reagent_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    reagent_id: UUID | None = None,
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_reagent_batches(page=page, page_size=page_size, reagent_id=str(reagent_id) if reagent_id else None, q=q, user=user)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/reagent-batches", response_model=ReagentBatchRead, dependencies=[Depends(require_permissions("inventory.manage"))])
def create_reagent_batch(payload: ReagentBatchCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_reagent_batch(payload, user, context)


@router.get("/reagent-usage", response_model=PaginatedResponse[ReagentUsageRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_reagent_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    reagent_id: UUID | None = None,
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_reagent_usage(page=page, page_size=page_size, reagent_id=str(reagent_id) if reagent_id else None, q=q)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/reagent-usage", response_model=ReagentUsageRead, dependencies=[Depends(require_permissions("inventory.manage"))])
def create_reagent_usage(payload: ReagentUsageCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_reagent_usage(payload, user, context)


@router.get("/reagent-wastage", response_model=PaginatedResponse[ReagentWastageRead], dependencies=[Depends(require_permissions("inventory.view"))])
def list_reagent_wastage(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    reagent_id: UUID | None = None,
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = InventoryService(db).list_reagent_wastage(page=page, page_size=page_size, reagent_id=str(reagent_id) if reagent_id else None, q=q)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/reagent-wastage", response_model=ReagentWastageRead, dependencies=[Depends(require_permissions("inventory.manage"))])
def create_reagent_wastage(payload: ReagentWastageCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return InventoryService(db).create_reagent_wastage(payload, user, context)
