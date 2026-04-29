from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.encounter import ERVisit, ERAmbulanceRecord


class ERRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_visits(self, branch_id=None) -> list[ERVisit]:
        stmt = (
            select(ERVisit)
            .options(joinedload(ERVisit.patient), joinedload(ERVisit.ambulance_records))
            .order_by(ERVisit.arrival_time.desc())
        )
        if branch_id:
            stmt = stmt.where(ERVisit.branch_id == branch_id)
        return list(self.db.scalars(stmt).unique())

    def get_visit(self, visit_id) -> ERVisit | None:
        stmt = (
            select(ERVisit)
            .options(joinedload(ERVisit.patient), joinedload(ERVisit.ambulance_records))
            .where(ERVisit.id == visit_id)
        )
        return self.db.scalar(stmt)

    def create_visit(self, visit: ERVisit) -> ERVisit:
        self.db.add(visit)
        self.db.flush()
        return visit

    def create_ambulance_record(self, ambulance: ERAmbulanceRecord) -> ERAmbulanceRecord:
        self.db.add(ambulance)
        self.db.flush()
        return ambulance

    def get_summary(self, branch_id=None) -> tuple[int, int, int, int, int, int, int, int]:
        stmt = select(
            func.count(ERVisit.id),
            func.count().filter(ERVisit.status == "waiting"),
            func.count().filter(ERVisit.status == "triaged"),
            func.count().filter(ERVisit.status == "assigned"),
            func.count().filter(ERVisit.status == "in_treatment"),
            func.count().filter(ERVisit.status == "admitted"),
            func.count().filter(ERVisit.status == "discharged"),
            func.count().filter(ERVisit.status == "referred"),
        )
        if branch_id:
            stmt = stmt.where(ERVisit.branch_id == branch_id)
        row = self.db.execute(stmt).one()
        return row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
