from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import BillingInvoice, BillingPayment, BillingRefund
from app.models.encounter import Appointment, IPDAdmission, OPDVisit, OPDVisitOrder
from app.models.pharmacy import PharmacyDispense


class ReportingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_clinical_summary(self, branch_id=None) -> dict[str, int | float]:
        opd_stmt = select(func.count(OPDVisit.id))
        opd_billed_stmt = select(func.count(OPDVisit.id)).where(OPDVisit.status == "billed")
        opd_completed_stmt = select(func.count(OPDVisit.id)).where(OPDVisit.status == "completed")
        scheduled_appointment_stmt = select(func.count(Appointment.id)).where(Appointment.status.in_(["scheduled", "confirmed"]))
        completed_appointment_stmt = select(func.count(Appointment.id)).where(Appointment.status == "completed")
        cancelled_appointment_stmt = select(func.count(Appointment.id)).where(Appointment.status == "cancelled")
        ipd_total_stmt = select(func.count(IPDAdmission.id))
        ipd_active_stmt = select(func.count(IPDAdmission.id)).where(IPDAdmission.status == "admitted")
        ipd_discharged_stmt = select(func.count(IPDAdmission.id)).where(IPDAdmission.status == "discharged")
        pharmacy_stmt = select(func.count(PharmacyDispense.id))
        pending_prescription_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "prescription",
            OPDVisitOrder.status == "pending",
        )
        pending_lab_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "laboratory",
            OPDVisitOrder.status.not_in(["completed", "verified"]),
        )
        completed_lab_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "laboratory",
            OPDVisitOrder.status == "completed",
        )
        verified_lab_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "laboratory",
            OPDVisitOrder.status == "verified",
        )
        pending_radiology_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "radiology",
            OPDVisitOrder.status.not_in(["completed", "verified"]),
        )
        completed_radiology_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "radiology",
            OPDVisitOrder.status == "completed",
        )
        verified_radiology_stmt = select(func.count(OPDVisitOrder.id)).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == "radiology",
            OPDVisitOrder.status == "verified",
        )
        unpaid_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "unpaid", BillingInvoice.status == "posted")
        partial_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "partial", BillingInvoice.status == "posted")
        paid_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "paid", BillingInvoice.status == "posted")
        payment_receipts_stmt = select(func.count(BillingPayment.id))
        collected_amount_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0))
        outstanding_due_stmt = select(func.coalesce(func.sum(BillingInvoice.due_amount), 0)).where(BillingInvoice.status == "posted")
        refunded_amount_stmt = select(func.coalesce(func.sum(BillingRefund.amount), 0))
        if branch_id:
            opd_stmt = opd_stmt.where(OPDVisit.branch_id == branch_id)
            opd_billed_stmt = opd_billed_stmt.where(OPDVisit.branch_id == branch_id)
            opd_completed_stmt = opd_completed_stmt.where(OPDVisit.branch_id == branch_id)
            scheduled_appointment_stmt = scheduled_appointment_stmt.where(Appointment.branch_id == branch_id)
            completed_appointment_stmt = completed_appointment_stmt.where(Appointment.branch_id == branch_id)
            cancelled_appointment_stmt = cancelled_appointment_stmt.where(Appointment.branch_id == branch_id)
            ipd_total_stmt = ipd_total_stmt.where(IPDAdmission.branch_id == branch_id)
            ipd_active_stmt = ipd_active_stmt.where(IPDAdmission.branch_id == branch_id)
            ipd_discharged_stmt = ipd_discharged_stmt.where(IPDAdmission.branch_id == branch_id)
            pharmacy_stmt = pharmacy_stmt.where(PharmacyDispense.branch_id == branch_id)
            pending_prescription_stmt = pending_prescription_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            pending_lab_stmt = pending_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            completed_lab_stmt = completed_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            verified_lab_stmt = verified_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            pending_radiology_stmt = pending_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            completed_radiology_stmt = completed_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            verified_radiology_stmt = verified_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            unpaid_invoice_stmt = unpaid_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            partial_invoice_stmt = partial_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            paid_invoice_stmt = paid_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            payment_receipts_stmt = payment_receipts_stmt.where(BillingPayment.branch_id == branch_id)
            collected_amount_stmt = collected_amount_stmt.where(BillingPayment.branch_id == branch_id)
            outstanding_due_stmt = outstanding_due_stmt.where(BillingInvoice.branch_id == branch_id)
            refunded_amount_stmt = refunded_amount_stmt.where(BillingRefund.branch_id == branch_id)
        return {
            "opd_visits": self.db.scalar(opd_stmt) or 0,
            "opd_billed_visits": self.db.scalar(opd_billed_stmt) or 0,
            "opd_completed_visits": self.db.scalar(opd_completed_stmt) or 0,
            "scheduled_appointments": self.db.scalar(scheduled_appointment_stmt) or 0,
            "completed_appointments": self.db.scalar(completed_appointment_stmt) or 0,
            "cancelled_appointments": self.db.scalar(cancelled_appointment_stmt) or 0,
            "ipd_total_admissions": self.db.scalar(ipd_total_stmt) or 0,
            "ipd_active_admissions": self.db.scalar(ipd_active_stmt) or 0,
            "ipd_discharged_admissions": self.db.scalar(ipd_discharged_stmt) or 0,
            "pharmacy_dispenses": self.db.scalar(pharmacy_stmt) or 0,
            "pending_prescriptions": self.db.scalar(pending_prescription_stmt) or 0,
            "pending_laboratory": self.db.scalar(pending_lab_stmt) or 0,
            "completed_laboratory": self.db.scalar(completed_lab_stmt) or 0,
            "verified_laboratory": self.db.scalar(verified_lab_stmt) or 0,
            "pending_radiology": self.db.scalar(pending_radiology_stmt) or 0,
            "completed_radiology": self.db.scalar(completed_radiology_stmt) or 0,
            "verified_radiology": self.db.scalar(verified_radiology_stmt) or 0,
            "unpaid_invoices": self.db.scalar(unpaid_invoice_stmt) or 0,
            "partial_invoices": self.db.scalar(partial_invoice_stmt) or 0,
            "paid_invoices": self.db.scalar(paid_invoice_stmt) or 0,
            "payment_receipts": self.db.scalar(payment_receipts_stmt) or 0,
            "collected_amount": float(self.db.scalar(collected_amount_stmt) or 0),
            "outstanding_due_amount": float(self.db.scalar(outstanding_due_stmt) or 0),
            "refunded_amount": float(self.db.scalar(refunded_amount_stmt) or 0),
        }
