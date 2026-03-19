from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingJournal


class AccountingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_journals(self, branch_id=None) -> list[AccountingJournal]:
        stmt = select(AccountingJournal).order_by(AccountingJournal.created_at.desc())
        if branch_id:
            stmt = stmt.where(AccountingJournal.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def create_journal(self, journal: AccountingJournal) -> AccountingJournal:
        self.db.add(journal)
        self.db.flush()
        return journal

