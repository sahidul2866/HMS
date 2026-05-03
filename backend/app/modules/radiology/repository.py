from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.radiology import RadiologyOrder, RadiologyReport, RadiologyReportSection, RadiologyAttachment, PACSLink
from app.models.encounter import OPDVisitOrder


class RadiologyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_orders(self, branch_id=None, status=None) -> list[RadiologyOrder]:
        stmt = (
            select(RadiologyOrder)
            .options(
                joinedload(RadiologyOrder.patient),
                joinedload(RadiologyOrder.visit),
            )
            .order_by(RadiologyOrder.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(RadiologyOrder.branch_id == branch_id)
        if status:
            stmt = stmt.where(RadiologyOrder.status == status)
        return list(self.db.scalars(stmt).unique())

    def get_order(self, order_id: UUID) -> RadiologyOrder | None:
        stmt = (
            select(RadiologyOrder)
            .options(
                joinedload(RadiologyOrder.patient),
                joinedload(RadiologyOrder.visit),
                joinedload(RadiologyOrder.reports).joinedload(RadiologyReport.sections),
                joinedload(RadiologyOrder.attachments),
                joinedload(RadiologyOrder.pacs_links),
            )
            .where(RadiologyOrder.id == order_id)
        )
        return self.db.scalar(stmt)

    def get_order_by_visit_order(self, visit_order_id: UUID) -> RadiologyOrder | None:
        stmt = select(RadiologyOrder).join(OPDVisitOrder, OPDVisitOrder.radiology_order_id == RadiologyOrder.id).where(OPDVisitOrder.id == visit_order_id)
        return self.db.scalar(stmt)

    def create_order(self, order: RadiologyOrder) -> RadiologyOrder:
        self.db.add(order)
        self.db.flush()
        return order

    def create_report(self, report: RadiologyReport) -> RadiologyReport:
        self.db.add(report)
        self.db.flush()
        return report

    def create_report_section(self, section: RadiologyReportSection) -> RadiologyReportSection:
        self.db.add(section)
        self.db.flush()
        return section

    def get_summary_counts(self, branch_id=None) -> dict[str, int]:
        stmt = select(
            func.count(RadiologyOrder.id),
            func.count().filter(RadiologyOrder.status == "pending"),
            func.count().filter(RadiologyOrder.status == "collected"),
            func.count().filter(RadiologyOrder.status == "in_progress"),
            func.count().filter(RadiologyOrder.status == "completed"),
            func.count().filter(RadiologyOrder.status == "verified"),
        )
        if branch_id:
            stmt = stmt.where(RadiologyOrder.branch_id == branch_id)
        row = self.db.execute(stmt).one()
        return {
            "total_orders": row[0],
            "pending_orders": row[1],
            "collected_orders": row[2],
            "in_progress_orders": row[3],
            "completed_orders": row[4],
            "verified_orders": row[5],
        }
