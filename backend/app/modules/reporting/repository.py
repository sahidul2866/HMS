from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.encounter import IPDAdmission, OPDVisit, OPDVisitOrder
from app.models.pharmacy import PharmacyDispense


class ReportingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_clinical_summary(self, branch_id=None) -> dict[str, int]:
        opd_stmt = select(func.count(OPDVisit.id))
        ipd_total_stmt = select(func.count(IPDAdmission.id))
        ipd_active_stmt = select(func.count(IPDAdmission.id)).where(IPDAdmission.status == "admitted")
        pharmacy_stmt = select(func.count(PharmacyDispense.id))
        pending_prescription_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "prescription",
            OPDVisitOrder.status == "pending",
        )
        pending_lab_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "laboratory",
            OPDVisitOrder.status != "completed",
        )
        completed_lab_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "laboratory",
            OPDVisitOrder.status == "completed",
        )
        pending_radiology_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "radiology",
            OPDVisitOrder.status != "completed",
        )
        completed_radiology_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "radiology",
            OPDVisitOrder.status == "completed",
        )
        if branch_id:
            opd_stmt = opd_stmt.where(OPDVisit.branch_id == branch_id)
            ipd_total_stmt = ipd_total_stmt.where(IPDAdmission.branch_id == branch_id)
            ipd_active_stmt = ipd_active_stmt.where(IPDAdmission.branch_id == branch_id)
            pharmacy_stmt = pharmacy_stmt.where(PharmacyDispense.branch_id == branch_id)
            pending_prescription_stmt = pending_prescription_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            pending_lab_stmt = pending_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            completed_lab_stmt = completed_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            pending_radiology_stmt = pending_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            completed_radiology_stmt = completed_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
        return {
            "opd_visits": self.db.scalar(opd_stmt) or 0,
            "ipd_total_admissions": self.db.scalar(ipd_total_stmt) or 0,
            "ipd_active_admissions": self.db.scalar(ipd_active_stmt) or 0,
            "pharmacy_dispenses": self.db.scalar(pharmacy_stmt) or 0,
            "pending_prescriptions": self.db.scalar(pending_prescription_stmt) or 0,
            "pending_laboratory": self.db.scalar(pending_lab_stmt) or 0,
            "completed_laboratory": self.db.scalar(completed_lab_stmt) or 0,
            "pending_radiology": self.db.scalar(pending_radiology_stmt) or 0,
            "completed_radiology": self.db.scalar(completed_radiology_stmt) or 0,
        }
