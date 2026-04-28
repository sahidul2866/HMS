from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.encounter import OPDVisit, OPDVisitOrder


class OPDRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_visits(self, branch_id=None, doctor_user_id=None) -> list[OPDVisit]:
        stmt = (
            select(OPDVisit)
            .options(joinedload(OPDVisit.patient), joinedload(OPDVisit.orders))
            .order_by(OPDVisit.visit_date.desc(), OPDVisit.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(OPDVisit.branch_id == branch_id)
        if doctor_user_id:
            stmt = stmt.where(OPDVisit.consulting_doctor_user_id == doctor_user_id)
        return list(self.db.scalars(stmt).unique())

    def get_visit(self, visit_id) -> OPDVisit | None:
        stmt = select(OPDVisit).options(joinedload(OPDVisit.patient), joinedload(OPDVisit.orders)).where(OPDVisit.id == visit_id)
        return self.db.scalars(stmt).unique().one_or_none()

    def create_visit(self, visit: OPDVisit) -> OPDVisit:
        self.db.add(visit)
        self.db.flush()
        return visit

    def create_order(self, order: OPDVisitOrder) -> OPDVisitOrder:
        self.db.add(order)
        self.db.flush()
        return order

    def get_order(self, order_id) -> OPDVisitOrder | None:
        stmt = (
            select(OPDVisitOrder)
            .options(joinedload(OPDVisitOrder.visit).joinedload(OPDVisit.patient))
            .where(OPDVisitOrder.id == order_id)
        )
        return self.db.scalar(stmt)

    def list_pending_prescription_orders(self, branch_id=None) -> list[OPDVisitOrder]:
        stmt = (
            select(OPDVisitOrder)
            .join(OPDVisitOrder.visit)
            .options(joinedload(OPDVisitOrder.visit).joinedload(OPDVisit.patient))
            .where(OPDVisitOrder.order_type == "prescription", OPDVisitOrder.status == "pending")
            .order_by(OPDVisit.created_at.desc(), OPDVisitOrder.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(OPDVisit.branch_id == branch_id)
        return list(self.db.scalars(stmt).unique())

    def list_investigation_orders(self, service_area: str, branch_id=None) -> list[OPDVisitOrder]:
        stmt = (
            select(OPDVisitOrder)
            .join(OPDVisitOrder.visit)
            .options(joinedload(OPDVisitOrder.visit).joinedload(OPDVisit.patient))
            .where(OPDVisitOrder.order_type == "investigation", OPDVisitOrder.service_area == service_area)
            .order_by(OPDVisit.visit_date.desc(), OPDVisitOrder.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(OPDVisit.branch_id == branch_id)
        return list(self.db.scalars(stmt).unique())

    def get_summary(self, branch_id=None, visit_date: date | None = None, doctor_user_id=None) -> tuple[int, int, int, int]:
        stmt = select(
            func.count(OPDVisit.id),
            func.count().filter(OPDVisit.status == "waiting"),
            func.count().filter(OPDVisit.status == "in_consultation"),
            func.count().filter(OPDVisit.status == "completed"),
        )
        if branch_id:
            stmt = stmt.where(OPDVisit.branch_id == branch_id)
        if visit_date:
            stmt = stmt.where(OPDVisit.visit_date == visit_date)
        if doctor_user_id:
            stmt = stmt.where(OPDVisit.consulting_doctor_user_id == doctor_user_id)
        row = self.db.execute(stmt).one()
        return row[0], row[1], row[2], row[3]
