from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.encounter import OPDVisit, OPDVisitOrder
from app.models.pharmacy import PharmacyDispense


class PharmacyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_dispenses(self, branch_id=None) -> list[PharmacyDispense]:
        stmt = (
            select(PharmacyDispense)
            .options(
                joinedload(PharmacyDispense.patient),
                joinedload(PharmacyDispense.source_visit),
                joinedload(PharmacyDispense.dispensed_by),
            )
            .order_by(PharmacyDispense.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(PharmacyDispense.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def create_dispense(self, dispense: PharmacyDispense) -> PharmacyDispense:
        self.db.add(dispense)
        self.db.flush()
        return dispense

    def get_dispense(self, dispense_id) -> PharmacyDispense | None:
        stmt = (
            select(PharmacyDispense)
            .options(
                joinedload(PharmacyDispense.patient),
                joinedload(PharmacyDispense.source_visit),
                joinedload(PharmacyDispense.dispensed_by),
                joinedload(PharmacyDispense.source_visit_order),
            )
            .where(PharmacyDispense.id == dispense_id)
        )
        return self.db.scalar(stmt)

    def get_net_dispensed_quantity(self, order_id) -> float:
        stmt = select(func.coalesce(func.sum(PharmacyDispense.quantity - PharmacyDispense.returned_quantity), 0)).where(
            PharmacyDispense.source_visit_order_id == order_id
        )
        return float(self.db.scalar(stmt) or 0)

    def get_summary(self, branch_id=None, summary_date: date | None = None) -> tuple[int, int, int, int, int, int]:
        today = summary_date or date.today()
        dispenses_stmt = select(
            func.count(PharmacyDispense.id),
            func.count().filter(func.date(PharmacyDispense.created_at) == today),
            func.count().filter(PharmacyDispense.status == "partial"),
            func.count().filter(PharmacyDispense.status.in_(["returned", "partially_returned"])),
        )
        if branch_id:
            dispenses_stmt = dispenses_stmt.where(PharmacyDispense.branch_id == branch_id)
        dispense_row = self.db.execute(dispenses_stmt).one()

        pending_stmt = (
            select(
                func.count(OPDVisitOrder.id),
                func.count().filter(OPDVisitOrder.visit.has(OPDVisit.status.in_(["billed", "completed"]))),
            )
            .where(OPDVisitOrder.order_type == "prescription", OPDVisitOrder.status.in_(["pending", "in_progress"]))
        )
        if branch_id:
            pending_stmt = pending_stmt.where(OPDVisitOrder.visit.has(OPDVisit.branch_id == branch_id))
        pending_row = self.db.execute(pending_stmt).one()

        return dispense_row[0], dispense_row[1], pending_row[0], pending_row[1], dispense_row[2], dispense_row[3]
