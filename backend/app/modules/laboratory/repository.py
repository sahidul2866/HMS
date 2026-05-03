from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.laboratory import LabOrder, LabOrderItem, LabResult, LabResultItem
from app.models.encounter import OPDVisitOrder


class LaboratoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_orders(self, branch_id=None, status=None) -> list[LabOrder]:
        stmt = (
            select(LabOrder)
            .options(
                joinedload(LabOrder.patient),
                joinedload(LabOrder.visit),
                joinedload(LabOrder.items),
            )
            .order_by(LabOrder.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(LabOrder.branch_id == branch_id)
        if status:
            stmt = stmt.where(LabOrder.status == status)
        return list(self.db.scalars(stmt).unique())

    def get_order(self, order_id: UUID) -> LabOrder | None:
        stmt = (
            select(LabOrder)
            .options(
                joinedload(LabOrder.patient),
                joinedload(LabOrder.visit),
                joinedload(LabOrder.items),
                joinedload(LabOrder.results).joinedload(LabResult.items),
                joinedload(LabOrder.attachments),
            )
            .where(LabOrder.id == order_id)
        )
        return self.db.scalar(stmt)

    def get_order_by_visit_order(self, visit_order_id: UUID) -> LabOrder | None:
        stmt = select(LabOrder).join(OPDVisitOrder, OPDVisitOrder.lab_order_id == LabOrder.id).where(OPDVisitOrder.id == visit_order_id)
        return self.db.scalar(stmt)

    def create_order(self, order: LabOrder) -> LabOrder:
        self.db.add(order)
        self.db.flush()
        return order

    def create_order_item(self, item: LabOrderItem) -> LabOrderItem:
        self.db.add(item)
        self.db.flush()
        return item

    def create_result(self, result: LabResult) -> LabResult:
        self.db.add(result)
        self.db.flush()
        return result

    def create_result_item(self, item: LabResultItem) -> LabResultItem:
        self.db.add(item)
        self.db.flush()
        return item

    def get_summary_counts(self, branch_id=None) -> dict[str, int]:
        stmt = select(
            func.count(LabOrder.id),
            func.count().filter(LabOrder.status == "pending"),
            func.count().filter(LabOrder.status == "collected"),
            func.count().filter(LabOrder.status == "in_progress"),
            func.count().filter(LabOrder.status == "completed"),
            func.count().filter(LabOrder.status == "verified"),
        )
        if branch_id:
            stmt = stmt.where(LabOrder.branch_id == branch_id)
        row = self.db.execute(stmt).one()
        return {
            "total_orders": row[0],
            "pending_orders": row[1],
            "collected_orders": row[2],
            "in_progress_orders": row[3],
            "completed_orders": row[4],
            "verified_orders": row[5],
        }
