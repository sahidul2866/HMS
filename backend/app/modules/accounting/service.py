from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.accounting import AccountingJournal
from app.models.user import User
from app.modules.accounting.repository import AccountingRepository
from app.modules.audit.service import AuditService
from app.schemas.accounting import AccountingJournalCreate
from app.utils.enums import AuditAction


class AccountingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AccountingRepository(db)

    def list_journals(self, actor: User) -> list[AccountingJournal]:
        return self.repository.list_journals(actor.branch_id)

    def post_journal(self, payload: AccountingJournalCreate, actor: User, context: dict[str, str | None]) -> AccountingJournal:
        sequence = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        journal = AccountingJournal(
            **payload.model_dump(),
            journal_number=f"JRN-{sequence}",
            branch_id=payload.branch_id or actor.branch_id,
            posted_by_user_id=actor.id,
            status="posted",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_journal(journal)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.ACCOUNTING_POST,
            module="accounting",
            entity_type="accounting_journal",
            entity_id=str(journal.id),
            detail={"journal_number": journal.journal_number, "reference": journal.reference},
            context=context,
        )
        self.db.commit()
        self.db.refresh(journal)
        return journal
