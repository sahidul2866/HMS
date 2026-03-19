from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.accounting.service import AccountingService
from app.schemas.accounting import AccountingJournalCreate, AccountingJournalRead

router = APIRouter(prefix="/accounting", tags=["Accounting"])


@router.get("/journals", response_model=list[AccountingJournalRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_journals(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AccountingJournalRead]:
    return [AccountingJournalRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_journals(user)]


@router.post("/journal/post", response_model=AccountingJournalRead, dependencies=[Depends(require_permissions("accounting.journal.post"))])
def post_journal(
    payload: AccountingJournalCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountingJournalRead:
    journal = AccountingService(db).post_journal(payload, user, context)
    return AccountingJournalRead.model_validate(journal, from_attributes=True)

