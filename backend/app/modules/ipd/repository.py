from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.encounter import (
    IPDAdmission,
    IPDAdmissionMovement,
    IPDBed,
    IPDClinicalNote,
    IPDHandover,
    IPDMedicationAdministration,
    IPDNursingNote,
    IPDNursingTask,
    IPDOrder,
    IPDStaffAssignment,
    IPDTimelineEvent,
)


class IPDRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_admissions(self, branch_id=None) -> list[IPDAdmission]:
        stmt = (
            select(IPDAdmission)
            .options(
                joinedload(IPDAdmission.patient),
                joinedload(IPDAdmission.bed),
                joinedload(IPDAdmission.movements),
                joinedload(IPDAdmission.orders),
                joinedload(IPDAdmission.handovers),
                joinedload(IPDAdmission.medication_administrations),
                joinedload(IPDAdmission.nursing_tasks),
            )
            .order_by(IPDAdmission.admitted_at.desc())
        )
        if branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == branch_id)
        return list(self.db.scalars(stmt).unique())

    def get_admission(self, admission_id) -> IPDAdmission | None:
        stmt = (
            select(IPDAdmission)
            .options(
                joinedload(IPDAdmission.patient),
                joinedload(IPDAdmission.bed),
                joinedload(IPDAdmission.movements),
                joinedload(IPDAdmission.staff_assignments),
                joinedload(IPDAdmission.clinical_notes),
                joinedload(IPDAdmission.nursing_notes),
                joinedload(IPDAdmission.orders),
                joinedload(IPDAdmission.medication_administrations),
                joinedload(IPDAdmission.nursing_tasks),
                joinedload(IPDAdmission.handovers),
                joinedload(IPDAdmission.timeline_events),
            )
            .where(IPDAdmission.id == admission_id)
        )
        return self.db.scalar(stmt)

    def create_admission(self, admission: IPDAdmission) -> IPDAdmission:
        self.db.add(admission)
        self.db.flush()
        return admission

    def create_movement(self, movement: IPDAdmissionMovement) -> IPDAdmissionMovement:
        self.db.add(movement)
        self.db.flush()
        return movement

    def get_summary(self, branch_id=None) -> tuple[int, int, int, int]:
        stmt = select(
            func.count(IPDAdmission.id),
            func.count().filter(IPDAdmission.status == "admitted"),
            func.count().filter(IPDAdmission.status == "discharged"),
            func.count().filter(IPDAdmission.status == "admitted"),
        )
        if branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == branch_id)
        row = self.db.execute(stmt).one()
        return row[0], row[1], row[2], row[3]

    def list_beds(self, branch_id=None) -> list[IPDBed]:
        stmt = select(IPDBed).order_by(IPDBed.ward_name.asc(), IPDBed.bed_number.asc())
        if branch_id:
            stmt = stmt.where(IPDBed.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def get_bed(self, bed_id) -> IPDBed | None:
        return self.db.get(IPDBed, bed_id)

    def get_bed_by_number(self, branch_id, ward_name: str, bed_number: str) -> IPDBed | None:
        stmt = select(IPDBed).where(IPDBed.ward_name == ward_name, IPDBed.bed_number == bed_number)
        if branch_id:
            stmt = stmt.where(IPDBed.branch_id == branch_id)
        return self.db.scalar(stmt)

    def create_bed(self, bed: IPDBed) -> IPDBed:
        self.db.add(bed)
        self.db.flush()
        return bed

    def create(self, entity):
        self.db.add(entity)
        self.db.flush()
        return entity
