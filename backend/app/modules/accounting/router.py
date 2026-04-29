from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.accounting.service import AccountingService
from app.schemas.accounting import (
    AccountCreate,
    AccountRead,
    AccountingDashboardRead,
    AccountingJournalCreate,
    AccountingJournalRead,
    AccountingWorkspaceRead,
    FinanceRecordRead,
    JournalEntryCreate,
    JournalEntryRead,
    SimpleFinanceCreate,
)

router = APIRouter(prefix="/accounting", tags=["Accounting"])


@router.get("/journals", response_model=list[AccountingJournalRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_journals(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AccountingJournalRead]:
    return [AccountingJournalRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_journals(user)]


@router.get("/dashboard", response_model=AccountingDashboardRead, dependencies=[Depends(require_permissions("accounting.view"))])
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)) -> AccountingDashboardRead:
    return AccountingService(db).dashboard(user)


@router.get("/workspace", response_model=AccountingWorkspaceRead, dependencies=[Depends(require_permissions("accounting.view"))])
def workspace(user=Depends(get_current_user), db: Session = Depends(get_db)) -> AccountingWorkspaceRead:
    return AccountingService(db).workspace(user)


@router.get("/accounts", response_model=list[AccountRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_accounts(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AccountRead]:
    return [AccountRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_accounts(user)]


@router.post("/accounts", response_model=AccountRead, dependencies=[Depends(require_permissions("accounting.manage"))])
def create_account(
    payload: AccountCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountRead:
    return AccountRead.model_validate(AccountingService(db).create_account(payload, user, context), from_attributes=True)


@router.get("/journal-entries", response_model=list[JournalEntryRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_journal_entries(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[JournalEntryRead]:
    return [JournalEntryRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_journal_entries(user)]


@router.post("/journal-entries", response_model=JournalEntryRead, dependencies=[Depends(require_permissions("accounting.journal.post"))])
def create_journal_entry(
    payload: JournalEntryCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalEntryRead:
    return JournalEntryRead.model_validate(AccountingService(db).create_journal_entry(payload, user, context), from_attributes=True)


@router.post("/{kind}", response_model=FinanceRecordRead, dependencies=[Depends(require_permissions("accounting.manage"))])
def create_finance_record(
    kind: str,
    payload: SimpleFinanceCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    entity = AccountingService(db).create_simple(kind, payload, user, context)
    return AccountingService(db)._finance_record(
        entity,
        getattr(entity, "receipt_number", None) or getattr(entity, "refund_number", None) or getattr(entity, "claim_number", None) or getattr(entity, "bill_number", None) or getattr(entity, "invoice_number", None) or getattr(entity, "expense_number", None) or kind,
        getattr(entity, "provider_name", None) or getattr(entity, "company_name", None) or getattr(entity, "supplier_name", None) or getattr(entity, "vendor_name", None) or kind.title(),
        getattr(entity, "amount", None) or getattr(entity, "claim_amount", None) or getattr(entity, "net_amount", None) or getattr(entity, "gross_amount", None) or 0,
        getattr(entity, "status", "created"),
        getattr(entity, "due_amount", 0),
        getattr(entity, "paid_amount", 0),
        getattr(entity, "category", None),
    )


@router.post("/journal/post", response_model=AccountingJournalRead, dependencies=[Depends(require_permissions("accounting.journal.post"))])
def post_journal(
    payload: AccountingJournalCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountingJournalRead:
    journal = AccountingService(db).post_journal(payload, user, context)
    return AccountingJournalRead.model_validate(journal, from_attributes=True)
