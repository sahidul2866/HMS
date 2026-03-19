from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pharmacy import PharmacyDispense


class PharmacyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_dispenses(self, branch_id=None) -> list[PharmacyDispense]:
        stmt = select(PharmacyDispense).order_by(PharmacyDispense.created_at.desc())
        if branch_id:
            stmt = stmt.where(PharmacyDispense.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def create_dispense(self, dispense: PharmacyDispense) -> PharmacyDispense:
        self.db.add(dispense)
        self.db.flush()
        return dispense

