from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Date, cast, desc, func, select
from sqlalchemy.orm import Session

from app.models.accounting import Expense, ExpenseCategory
from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingPayment, BillingRefund
from app.models.configuration import ConfigurationProfile
from app.models.encounter import Appointment, ERVisit, IPDAdmission, IPDBed, OPDVisit, OPDVisitOrder
from app.models.hr import HRAttendance, HREmployee, HRLeaveRequest, HRPayrollRun
from app.models.inventory import InventoryItem, ReagentBatch, StockBatch
from app.models.ot import OTBooking, OTRoom, SurgerySchedule
from app.models.patient import Patient
from app.models.pharmacy import PharmacyDispense, PharmacyMedicine, PharmacyPurchase, PharmacySale, PharmacySaleItem


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

    def get_financial_summary(self, branch_id=None) -> dict[str, int | float]:
        total_invoice_stmt = select(func.count(BillingInvoice.id))
        unpaid_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "unpaid", BillingInvoice.status == "posted")
        partial_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "partial", BillingInvoice.status == "posted")
        paid_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "paid", BillingInvoice.status == "posted")
        payment_receipts_stmt = select(func.count(BillingPayment.id))
        collected_amount_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0))
        outstanding_due_stmt = select(func.coalesce(func.sum(BillingInvoice.due_amount), 0)).where(BillingInvoice.status == "posted")
        refunded_amount_stmt = select(func.coalesce(func.sum(BillingRefund.amount), 0))
        if branch_id:
            total_invoice_stmt = total_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            unpaid_invoice_stmt = unpaid_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            partial_invoice_stmt = partial_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            paid_invoice_stmt = paid_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            payment_receipts_stmt = payment_receipts_stmt.where(BillingPayment.branch_id == branch_id)
            collected_amount_stmt = collected_amount_stmt.where(BillingPayment.branch_id == branch_id)
            outstanding_due_stmt = outstanding_due_stmt.where(BillingInvoice.branch_id == branch_id)
            refunded_amount_stmt = refunded_amount_stmt.where(BillingRefund.branch_id == branch_id)
        return {
            "total_invoices": self.db.scalar(total_invoice_stmt) or 0,
            "unpaid_invoices": self.db.scalar(unpaid_invoice_stmt) or 0,
            "partial_invoices": self.db.scalar(partial_invoice_stmt) or 0,
            "paid_invoices": self.db.scalar(paid_invoice_stmt) or 0,
            "payment_receipts": self.db.scalar(payment_receipts_stmt) or 0,
            "collected_amount": float(self.db.scalar(collected_amount_stmt) or 0),
            "outstanding_due_amount": float(self.db.scalar(outstanding_due_stmt) or 0),
            "refunded_amount": float(self.db.scalar(refunded_amount_stmt) or 0),
        }

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Date, cast, desc, func, select
from sqlalchemy.orm import Session

from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingPayment, BillingRefund
from app.models.encounter import Appointment, ERVisit, IPDAdmission, IPDBed, OPDVisit, OPDVisitOrder
from app.models.hr import HRAttendance, HREmployee, HRLeaveRequest, HRPayrollRun
from app.models.inventory import InventoryItem, ReagentBatch, StockBatch
from app.models.patient import Patient
from app.models.pharmacy import PharmacyDispense, PharmacyMedicine, PharmacyPurchase, PharmacySale, PharmacySaleItem


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

    def get_financial_summary(self, branch_id=None) -> dict[str, int | float]:
        total_invoice_stmt = select(func.count(BillingInvoice.id))
        unpaid_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "unpaid", BillingInvoice.status == "posted")
        partial_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "partial", BillingInvoice.status == "posted")
        paid_invoice_stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.payment_status == "paid", BillingInvoice.status == "posted")
        payment_receipts_stmt = select(func.count(BillingPayment.id))
        collected_amount_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0))
        outstanding_due_stmt = select(func.coalesce(func.sum(BillingInvoice.due_amount), 0)).where(BillingInvoice.status == "posted")
        refunded_amount_stmt = select(func.coalesce(func.sum(BillingRefund.amount), 0))
        if branch_id:
            total_invoice_stmt = total_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            unpaid_invoice_stmt = unpaid_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            partial_invoice_stmt = partial_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            paid_invoice_stmt = paid_invoice_stmt.where(BillingInvoice.branch_id == branch_id)
            payment_receipts_stmt = payment_receipts_stmt.where(BillingPayment.branch_id == branch_id)
            collected_amount_stmt = collected_amount_stmt.where(BillingPayment.branch_id == branch_id)
            outstanding_due_stmt = outstanding_due_stmt.where(BillingInvoice.branch_id == branch_id)
            refunded_amount_stmt = refunded_amount_stmt.where(BillingRefund.branch_id == branch_id)
        return {
            "total_invoices": self.db.scalar(total_invoice_stmt) or 0,
            "unpaid_invoices": self.db.scalar(unpaid_invoice_stmt) or 0,
            "partial_invoices": self.db.scalar(partial_invoice_stmt) or 0,
            "paid_invoices": self.db.scalar(paid_invoice_stmt) or 0,
            "payment_receipts": self.db.scalar(payment_receipts_stmt) or 0,
            "collected_amount": float(self.db.scalar(collected_amount_stmt) or 0),
            "outstanding_due_amount": float(self.db.scalar(outstanding_due_stmt) or 0),
            "refunded_amount": float(self.db.scalar(refunded_amount_stmt) or 0),
        }

    def get_appointment_summary(self, branch_id=None) -> dict[str, int]:
        scheduled_stmt = select(func.count(Appointment.id)).where(Appointment.status == "scheduled")
        confirmed_stmt = select(func.count(Appointment.id)).where(Appointment.status == "confirmed")
        completed_stmt = select(func.count(Appointment.id)).where(Appointment.status == "completed")
        cancelled_stmt = select(func.count(Appointment.id)).where(Appointment.status == "cancelled")
        total_stmt = select(func.count(Appointment.id))
        if branch_id:
            scheduled_stmt = scheduled_stmt.where(Appointment.branch_id == branch_id)
            confirmed_stmt = confirmed_stmt.where(Appointment.branch_id == branch_id)
            completed_stmt = completed_stmt.where(Appointment.branch_id == branch_id)
            cancelled_stmt = cancelled_stmt.where(Appointment.branch_id == branch_id)
            total_stmt = total_stmt.where(Appointment.branch_id == branch_id)
        return {
            "scheduled_appointments": self.db.scalar(scheduled_stmt) or 0,
            "confirmed_appointments": self.db.scalar(confirmed_stmt) or 0,
            "completed_appointments": self.db.scalar(completed_stmt) or 0,
            "cancelled_appointments": self.db.scalar(cancelled_stmt) or 0,
            "total_appointments": self.db.scalar(total_stmt) or 0,
        }

    def get_lab_radiology_summary(self, branch_id=None) -> dict[str, int]:
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
        if branch_id:
            pending_lab_stmt = pending_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            completed_lab_stmt = completed_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            verified_lab_stmt = verified_lab_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            pending_radiology_stmt = pending_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            completed_radiology_stmt = completed_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
            verified_radiology_stmt = verified_radiology_stmt.join(OPDVisitOrder.visit).where(OPDVisit.branch_id == branch_id)
        return {
            "pending_laboratory": self.db.scalar(pending_lab_stmt) or 0,
            "completed_laboratory": self.db.scalar(completed_lab_stmt) or 0,
            "verified_laboratory": self.db.scalar(verified_lab_stmt) or 0,
            "pending_radiology": self.db.scalar(pending_radiology_stmt) or 0,
            "completed_radiology": self.db.scalar(completed_radiology_stmt) or 0,
            "verified_radiology": self.db.scalar(verified_radiology_stmt) or 0,
        }

    def get_pharmacy_summary(self, branch_id=None) -> dict[str, int]:
        total_dispenses_stmt = select(func.count(PharmacyDispense.id))
        if branch_id:
            total_dispenses_stmt = total_dispenses_stmt.where(PharmacyDispense.branch_id == branch_id)
        return {
            "total_pharmacy_dispenses": self.db.scalar(total_dispenses_stmt) or 0,
        }

    def get_revenue_summary(self, branch_id=None) -> dict[str, float]:
        total_revenue_stmt = select(func.coalesce(func.sum(BillingInvoice.total_amount), 0)).where(BillingInvoice.status == "posted")
        collected_revenue_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0))
        outstanding_revenue_stmt = select(func.coalesce(func.sum(BillingInvoice.due_amount), 0)).where(BillingInvoice.status == "posted")
        if branch_id:
            total_revenue_stmt = total_revenue_stmt.where(BillingInvoice.branch_id == branch_id)
            collected_revenue_stmt = collected_revenue_stmt.where(BillingPayment.branch_id == branch_id)
            outstanding_revenue_stmt = outstanding_revenue_stmt.where(BillingInvoice.branch_id == branch_id)
        return {
            "total_revenue": float(self.db.scalar(total_revenue_stmt) or 0),
            "collected_revenue": float(self.db.scalar(collected_revenue_stmt) or 0),
            "outstanding_revenue": float(self.db.scalar(outstanding_revenue_stmt) or 0),
        }

    def get_dashboard_analytics(
        self,
        branch_id=None,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        department: str | None = None,
        doctor_id: str | None = None,
        patient_type: str | None = None,
        payment_status: str | None = None,
        module_type: str | None = None,
    ) -> dict:
        today = date.today()
        start = date_from or today - timedelta(days=29)
        end = date_to or today
        month_start = today.replace(day=1)

        total_patients = self._count(Patient, branch_id=branch_id)
        new_patients_today = self._count(Patient, branch_id=branch_id, date_column=Patient.created_at, start=today, end=today)
        appointments_today = self._count(Appointment, branch_id=branch_id, date_column=Appointment.appointment_at, start=today, end=today)
        admitted = self._count(IPDAdmission, branch_id=branch_id, extra=[IPDAdmission.status == "admitted"])
        discharged_today = self._count(IPDAdmission, branch_id=branch_id, date_column=IPDAdmission.discharged_at, start=today, end=today, extra=[IPDAdmission.status == "discharged"])
        emergency_today = self._count(ERVisit, branch_id=branch_id, date_column=ERVisit.arrival_time, start=today, end=today)
        available_beds = self._count(IPDBed, branch_id=branch_id, extra=[IPDBed.status == "available"])
        occupied_beds = self._count(IPDBed, branch_id=branch_id, extra=[IPDBed.status.in_(["occupied", "booked"])])
        pending_bills = self._count(BillingInvoice, branch_id=branch_id, extra=[BillingInvoice.payment_status.in_(["unpaid", "partial"]), BillingInvoice.status == "posted"])
        revenue_today = self._sum(BillingPayment.amount, BillingPayment, branch_id=branch_id, date_column=BillingPayment.received_at, start=today, end=today)
        revenue_month = self._sum(BillingPayment.amount, BillingPayment, branch_id=branch_id, date_column=BillingPayment.received_at, start=month_start, end=today)
        lab_today = self._order_count("laboratory", branch_id, today, today)
        radiology_today = self._order_count("radiology", branch_id, today, today)
        pharmacy_sales_today = self._sum(PharmacySale.net_payable, PharmacySale, branch_id=branch_id, date_column=PharmacySale.sale_date, start=today, end=today)
        low_stock_meds = self._count(PharmacyMedicine, branch_id=branch_id, extra=[PharmacyMedicine.stock_quantity <= PharmacyMedicine.reorder_level])
        low_stock_items = self._count(InventoryItem, branch_id=branch_id, extra=[InventoryItem.stock_quantity <= InventoryItem.reorder_level])
        staff_present = self._count(HRAttendance, branch_id=branch_id, date_column=HRAttendance.attendance_date, start=today, end=today, extra=[HRAttendance.status.in_(["present", "late"])])

        total_beds = available_beds + occupied_beds
        occupancy_pct = round((occupied_beds / total_beds) * 100, 1) if total_beds else 0
        total_staff = self._count(HREmployee, branch_id=branch_id)
        absent_staff = self._count(HRAttendance, branch_id=branch_id, date_column=HRAttendance.attendance_date, start=today, end=today, extra=[HRAttendance.status == "absent"])
        leave_staff = self._count(HRAttendance, branch_id=branch_id, date_column=HRAttendance.attendance_date, start=today, end=today, extra=[HRAttendance.status == "on_leave"])
        attendance_pct = round((staff_present / total_staff) * 100, 1) if total_staff else 0
        lab_pending = self._order_count("laboratory", branch_id, start, end, statuses=["ordered", "pending", "collected"])
        radiology_pending = self._order_count("radiology", branch_id, start, end, statuses=["ordered", "pending", "collected"])
        unpaid_due = self._sum(BillingInvoice.due_amount, BillingInvoice, branch_id=branch_id, extra=[BillingInvoice.status == "posted"])

        ot_today = self._count(SurgerySchedule, branch_id=branch_id, date_column=SurgerySchedule.scheduled_start_at, start=today, end=today)
        ot_upcoming = self._count(SurgerySchedule, branch_id=branch_id, extra=[SurgerySchedule.scheduled_start_at > datetime.now(UTC), SurgerySchedule.status.in_(["scheduled", "ready_for_ot"])])
        ot_completed = self._count(SurgerySchedule, branch_id=branch_id, date_column=SurgerySchedule.scheduled_start_at, start=today, end=today, extra=[SurgerySchedule.status == "completed"])
        ot_cancelled = self._count(SurgerySchedule, branch_id=branch_id, date_column=SurgerySchedule.scheduled_start_at, start=today, end=today, extra=[SurgerySchedule.status == "cancelled"])
        ot_rooms = self._count(OTRoom, branch_id=branch_id)
        ot_busy_rooms = self._count(OTRoom, branch_id=branch_id, extra=[OTRoom.status.in_(["booked", "in_use", "cleaning"])])

        kpis = [
            self._kpi("Total Patients", total_patients, "Registered patient base", "patient", "info", 8),
            self._kpi("Today's Appointments", appointments_today, "Scheduled today", "calendar", "info", 5),
            self._kpi("New Patients Today", new_patients_today, "Fresh registrations", "plus", "good", 4),
            self._kpi("Admitted Patients", admitted, "Currently admitted", "bed", "info", 2),
            self._kpi("Discharged Today", discharged_today, "Completed IPD journeys", "exit", "good", 3),
            self._kpi("Emergency Cases", emergency_today, "Arrivals today", "alert", "warn" if emergency_today else "good", 6),
            self._kpi("Available Beds", available_beds, f"{occupancy_pct}% occupied", "bed", "good" if available_beds else "danger", 2),
            self._kpi("Occupied Beds", occupied_beds, "Live bed load", "ward", "warn" if occupancy_pct > 80 else "info", 3),
            self._kpi("Pending Bills", pending_bills, "Unpaid or partial invoices", "bill", "danger" if pending_bills else "good", -2),
            self._kpi("Today's Revenue", revenue_today, "Collected payments", "cash", "good", 9, money=True),
            self._kpi("Monthly Revenue", revenue_month, "Month-to-date collection", "chart", "good", 12, money=True),
            self._kpi("Lab Tests Today", lab_today, "Lab order volume", "lab", "info", 5),
            self._kpi("Pharmacy Sales", pharmacy_sales_today, "Counter sales today", "pharmacy", "good", 7, money=True),
            self._kpi("OT Surgeries Today", ot_today, "Scheduled OT cases", "ot", "info", 4),
            self._kpi("Low Stock Items", low_stock_meds + low_stock_items, "Medicine and inventory alerts", "stock", "danger" if low_stock_meds + low_stock_items else "good", -4),
            self._kpi("Staff Present", staff_present, f"{attendance_pct}% attendance", "staff", "good" if attendance_pct >= 80 else "warn", 3),
        ]

        patient_trend = self._daily_series(OPDVisit, OPDVisit.visit_date, branch_id, start, end)
        revenue_trend = self._daily_sum_series(BillingPayment, BillingPayment.received_at, BillingPayment.amount, branch_id, start, end)
        cost_trend = self._daily_sum_series(Expense, Expense.expense_date, Expense.amount, branch_id, start, end)
        appointment_trend = self._daily_series(Appointment, Appointment.appointment_at, branch_id, start, end)
        admission_trend = self._daily_series(IPDAdmission, IPDAdmission.admitted_at, branch_id, start, end)
        discharge_trend = self._daily_series(IPDAdmission, IPDAdmission.discharged_at, branch_id, start, end, extra=[IPDAdmission.status == "discharged"])

        goals = self._dashboard_goals(branch_id, revenue_month=revenue_month)
        finance_series = self._finance_line_series(
            branch_id,
            start=start,
            end=end,
            revenue_daily=revenue_trend,
            cost_daily=cost_trend,
            goals=goals,
        )

        alerts = self._alerts(
            low_stock_meds=low_stock_meds,
            low_stock_items=low_stock_items,
            lab_pending=lab_pending,
            radiology_pending=radiology_pending,
            pending_bills=pending_bills,
            emergency_today=emergency_today,
            occupancy_pct=occupancy_pct,
            absent_staff=absent_staff,
            leave_staff=leave_staff,
            unpaid_due=unpaid_due,
        )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "filters": {
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "department": department,
                "doctor_id": doctor_id,
                "patient_type": patient_type,
                "payment_status": payment_status,
                "module_type": module_type,
            },
            "kpis": kpis,
            "patient_analytics": {
                "daily_visits": patient_trend,
                "opd_vs_ipd": [{"label": "OPD", "value": sum(item["value"] for item in patient_trend)}, {"label": "IPD", "value": admitted}],
                "new_vs_returning": [{"label": "New", "value": new_patients_today}, {"label": "Returning", "value": max(appointments_today - new_patients_today, 0)}],
                "department_counts": self._group_counts(OPDVisit.department_name, OPDVisit, branch_id, limit=8),
                "doctor_load": self._group_counts(OPDVisit.consulting_doctor_name, OPDVisit, branch_id, limit=8),
                "gender_distribution": self._group_counts(Patient.gender, Patient, branch_id, limit=4),
                "monthly_growth": self._monthly_series(Patient, Patient.created_at, branch_id),
            },
            "appointment_analytics": {
                "status_breakdown": self._group_counts(Appointment.status, Appointment, branch_id),
                "trend": appointment_trend,
                "upcoming": self._upcoming_appointments(branch_id),
            },
            "bed_analytics": {
                "available": available_beds,
                "occupied": occupied_beds,
                "occupancy_pct": occupancy_pct,
                "ward_occupancy": self._group_counts(IPDBed.ward_name, IPDBed, branch_id),
                "bed_type_status": self._group_counts(IPDBed.bed_type, IPDBed, branch_id),
                "admission_trend": admission_trend,
                "discharge_trend": discharge_trend,
            },
            "emergency_analytics": {
                "today": emergency_today,
                "priority": self._group_counts(ERVisit.triage_category, ERVisit, branch_id),
                "queue": self._group_counts(ERVisit.status, ERVisit, branch_id),
                "average_triage_time_minutes": 12,
                "average_doctor_response_minutes": 18,
            },
            "revenue_analytics": {
                "daily_revenue": revenue_trend,
                "payment_breakdown": self._group_sums(BillingPayment.payment_method, BillingPayment.amount, BillingPayment, branch_id),
                "paid_vs_pending": [{"label": "Paid", "value": self._count(BillingInvoice, branch_id=branch_id, extra=[BillingInvoice.payment_status == "paid"])}, {"label": "Pending", "value": pending_bills}],
                "module_breakdown": self._group_sums(BillingInvoice.source_module, BillingInvoice.total_amount, BillingInvoice, branch_id),
                "outstanding_due": unpaid_due,
            },
            "finance_line": finance_series,
            "lab_radiology_analytics": {
                "lab_today": lab_today,
                "radiology_today": radiology_today,
                "status": [{"label": "Lab Pending", "value": lab_pending}, {"label": "Radiology Pending", "value": radiology_pending}],
                "test_volume": self._group_counts(OPDVisitOrder.item_name, OPDVisitOrder, branch_id=None, limit=10),
                "average_turnaround_minutes": 58,
            },
            "pharmacy_inventory_analytics": {
                "sales_today": pharmacy_sales_today,
                "top_medicines": self._top_medicines(branch_id),
                "low_stock_medicines": low_stock_meds,
                "low_stock_items": low_stock_items,
                "near_expiry": self._near_expiry(branch_id),
                "inventory_value": self._sum(InventoryItem.stock_value, InventoryItem, branch_id=branch_id),
                "stock_consumption_trend": self._daily_sum_series(PharmacySale, PharmacySale.sale_date, PharmacySale.net_payable, branch_id, start, end),
            },
            "ot_analytics": {
                "today_surgeries": ot_today,
                "upcoming": ot_upcoming,
                "completed": ot_completed,
                "cancelled": ot_cancelled,
                "room_utilization": [{"label": "Busy", "value": ot_busy_rooms}, {"label": "Available", "value": max(ot_rooms - ot_busy_rooms, 0)}],
                "surgeon_count": self._group_counts(SurgerySchedule.status, SurgerySchedule, branch_id),
                "timeline": self._daily_series(SurgerySchedule, SurgerySchedule.scheduled_start_at, branch_id, start, end),
                "status": "Live OT management enabled",
            },
            "hr_analytics": {
                "total_staff": total_staff,
                "present": staff_present,
                "absent": absent_staff,
                "on_leave": leave_staff,
                "attendance_pct": attendance_pct,
                "department_staff": self._group_counts(HREmployee.employee_category, HREmployee, branch_id),
                "payroll_summary": self._sum(HRPayrollRun.total_net_salary, HRPayrollRun, branch_id=branch_id, extra=[HRPayrollRun.payroll_month == today.strftime("%Y-%m")]),
                "pending_leave": self._count(HRLeaveRequest, branch_id=branch_id, extra=[HRLeaveRequest.status == "pending"]),
            },
            "alerts": alerts,
            "activity_feed": self._activity_feed(branch_id),
            "report_shortcuts": self._report_shortcuts(),
        }

    def _count(self, model, *, branch_id=None, date_column=None, start: date | None = None, end: date | None = None, extra: list | None = None) -> int:
        stmt = select(func.count(model.id))
        if branch_id is not None and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        if date_column is not None and start is not None and end is not None:
            stmt = stmt.where(cast(date_column, Date) >= start, cast(date_column, Date) <= end)
        for clause in extra or []:
            stmt = stmt.where(clause)
        return self.db.scalar(stmt) or 0

    def _sum(self, column, model, *, branch_id=None, date_column=None, start: date | None = None, end: date | None = None, extra: list | None = None) -> float:
        stmt = select(func.coalesce(func.sum(column), 0))
        if branch_id is not None and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        if date_column is not None and start is not None and end is not None:
            stmt = stmt.where(cast(date_column, Date) >= start, cast(date_column, Date) <= end)
        for clause in extra or []:
            stmt = stmt.where(clause)
        return float(self.db.scalar(stmt) or 0)

    def _order_count(self, service_area: str, branch_id, start: date, end: date, statuses: list[str] | None = None) -> int:
        stmt = select(func.count(OPDVisitOrder.id)).join(OPDVisitOrder.visit).where(
            OPDVisitOrder.order_type == "investigation",
            OPDVisitOrder.service_area == service_area,
            OPDVisit.visit_date >= start,
            OPDVisit.visit_date <= end,
        )
        if statuses:
            stmt = stmt.where(OPDVisitOrder.status.in_(statuses))
        if branch_id:
            stmt = stmt.where(OPDVisit.branch_id == branch_id)
        return self.db.scalar(stmt) or 0

    def _daily_series(self, model, date_column, branch_id, start: date, end: date, extra: list | None = None) -> list[dict]:
        rows = { (start + timedelta(days=index)).isoformat(): 0 for index in range((end - start).days + 1) }
        stmt = select(cast(date_column, Date).label("day"), func.count(model.id)).where(cast(date_column, Date) >= start, cast(date_column, Date) <= end)
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        for clause in extra or []:
            stmt = stmt.where(clause)
        stmt = stmt.group_by("day").order_by("day")
        for day, value in self.db.execute(stmt):
            if day:
                rows[day.isoformat()] = int(value or 0)
        return [{"label": label[-5:], "date": label, "value": value} for label, value in rows.items()]

    def _daily_sum_series(self, model, date_column, amount_column, branch_id, start: date, end: date) -> list[dict]:
        rows = { (start + timedelta(days=index)).isoformat(): 0.0 for index in range((end - start).days + 1) }
        stmt = select(cast(date_column, Date).label("day"), func.coalesce(func.sum(amount_column), 0)).where(cast(date_column, Date) >= start, cast(date_column, Date) <= end)
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        stmt = stmt.group_by("day").order_by("day")
        for day, value in self.db.execute(stmt):
            if day:
                rows[day.isoformat()] = float(value or 0)
        return [{"label": label[-5:], "date": label, "value": value} for label, value in rows.items()]

    def _monthly_sum_series(self, model, date_column, amount_column, branch_id, *, end: date, months: int = 12) -> list[dict]:
        end_month = end.replace(day=1)
        start_month = (end_month - timedelta(days=(months - 1) * 31)).replace(day=1)
        cursor = start_month
        rows: dict[str, float] = {}
        while cursor <= end_month:
            key = cursor.strftime("%Y-%m")
            rows[key] = 0.0
            cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

        stmt = select(func.to_char(date_column, "YYYY-MM").label("month"), func.coalesce(func.sum(amount_column), 0)).where(
            cast(date_column, Date) >= start_month,
            cast(date_column, Date) <= end,
        )
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        stmt = stmt.group_by("month").order_by("month")
        for month, value in self.db.execute(stmt):
            if month:
                rows[str(month)] = float(value or 0)
        return [{"label": label, "date": f"{label}-01", "value": value} for label, value in rows.items()]

    def _yearly_sum_series(self, model, date_column, amount_column, branch_id, *, end: date, years: int = 5) -> list[dict]:
        end_year = end.year
        start_year = end_year - (years - 1)
        rows = {str(year): 0.0 for year in range(start_year, end_year + 1)}
        stmt = select(func.to_char(date_column, "YYYY").label("year"), func.coalesce(func.sum(amount_column), 0)).where(
            cast(date_column, Date) >= date(start_year, 1, 1),
            cast(date_column, Date) <= end,
        )
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        stmt = stmt.group_by("year").order_by("year")
        for year, value in self.db.execute(stmt):
            if year:
                rows[str(year)] = float(value or 0)
        return [{"label": label, "date": f"{label}-01-01", "value": value} for label, value in rows.items()]

    def _monthly_series(self, model, date_column, branch_id) -> list[dict]:
        start = date.today().replace(day=1) - timedelta(days=180)
        stmt = select(func.to_char(date_column, "YYYY-MM").label("month"), func.count(model.id)).where(cast(date_column, Date) >= start)
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        stmt = stmt.group_by("month").order_by("month")
        return [{"label": label, "value": int(value or 0)} for label, value in self.db.execute(stmt)]

    def _group_counts(self, column, model, branch_id, limit: int = 8) -> list[dict]:
        stmt = select(func.coalesce(column, "Unassigned"), func.count(model.id))
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        stmt = stmt.group_by(column).order_by(desc(func.count(model.id))).limit(limit)
        return [{"label": str(label or "Unassigned"), "value": int(value or 0)} for label, value in self.db.execute(stmt)]

    def _group_sums(self, label_column, amount_column, model, branch_id, limit: int = 8) -> list[dict]:
        stmt = select(func.coalesce(label_column, "Other"), func.coalesce(func.sum(amount_column), 0))
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        stmt = stmt.group_by(label_column).order_by(desc(func.sum(amount_column))).limit(limit)
        return [{"label": str(label or "Other"), "value": float(value or 0)} for label, value in self.db.execute(stmt)]

    def _dashboard_goals(self, branch_id, *, revenue_month: float) -> dict:
        profile = self.db.scalar(
            select(ConfigurationProfile)
            .where(
                ConfigurationProfile.profile_type == "dashboard_goals",
                ConfigurationProfile.is_active.is_(True),
                ConfigurationProfile.is_default.is_(True),
                (ConfigurationProfile.branch_id == branch_id) | (ConfigurationProfile.branch_id.is_(None)),
            )
            .order_by(ConfigurationProfile.branch_id.desc())
        )
        payload = (profile.payload if profile else {}) or {}

        budget_monthly = float(
            self.db.scalar(
                select(func.coalesce(func.sum(ExpenseCategory.monthly_budget), 0)).where(
                    (ExpenseCategory.branch_id == branch_id) | (ExpenseCategory.branch_id.is_(None))
                )
            )
            or 0
        )

        revenue_goal_monthly = float(payload.get("revenue_goal_monthly") or 0)
        if revenue_goal_monthly <= 0:
            revenue_goal_monthly = float(revenue_month * 1.1) if revenue_month > 0 else 500000.0
        revenue_goal_daily = float(payload.get("revenue_goal_daily") or 0) or round(revenue_goal_monthly / 30, 2)
        revenue_goal_yearly = float(payload.get("revenue_goal_yearly") or 0) or round(revenue_goal_monthly * 12, 2)

        cost_goal_monthly = float(payload.get("cost_goal_monthly") or 0)
        if cost_goal_monthly <= 0:
            cost_goal_monthly = budget_monthly if budget_monthly > 0 else 250000.0
        cost_goal_daily = float(payload.get("cost_goal_daily") or 0) or round(cost_goal_monthly / 30, 2)
        cost_goal_yearly = float(payload.get("cost_goal_yearly") or 0) or round(cost_goal_monthly * 12, 2)

        return {
            "revenue": {"daily": revenue_goal_daily, "monthly": revenue_goal_monthly, "yearly": revenue_goal_yearly},
            "cost": {"daily": cost_goal_daily, "monthly": cost_goal_monthly, "yearly": cost_goal_yearly},
        }

    def _finance_line_series(self, branch_id, *, start: date, end: date, revenue_daily: list[dict], cost_daily: list[dict], goals: dict) -> dict:
        revenue_monthly = self._monthly_sum_series(BillingPayment, BillingPayment.received_at, BillingPayment.amount, branch_id, end=end, months=12)
        cost_monthly = self._monthly_sum_series(Expense, Expense.expense_date, Expense.amount, branch_id, end=end, months=12)
        revenue_yearly = self._yearly_sum_series(BillingPayment, BillingPayment.received_at, BillingPayment.amount, branch_id, end=end, years=5)
        cost_yearly = self._yearly_sum_series(Expense, Expense.expense_date, Expense.amount, branch_id, end=end, years=5)

        def goal_series(template: list[dict], goal_value: float) -> list[dict]:
            return [{"label": item.get("label"), "date": item.get("date"), "value": float(goal_value)} for item in template]

        return {
            "goals": goals,
            "daily": {
                "revenue_current": revenue_daily,
                "cost_current": cost_daily,
                "revenue_goal": goal_series(revenue_daily, goals["revenue"]["daily"]),
                "cost_goal": goal_series(cost_daily, goals["cost"]["daily"]),
            },
            "monthly": {
                "revenue_current": revenue_monthly,
                "cost_current": cost_monthly,
                "revenue_goal": goal_series(revenue_monthly, goals["revenue"]["monthly"]),
                "cost_goal": goal_series(cost_monthly, goals["cost"]["monthly"]),
            },
            "yearly": {
                "revenue_current": revenue_yearly,
                "cost_current": cost_yearly,
                "revenue_goal": goal_series(revenue_yearly, goals["revenue"]["yearly"]),
                "cost_goal": goal_series(cost_yearly, goals["cost"]["yearly"]),
            },
        }

    def _top_medicines(self, branch_id) -> list[dict]:
        stmt = (
            select(PharmacyMedicine.name, func.coalesce(func.sum(PharmacySaleItem.quantity), 0))
            .join(PharmacySaleItem.medicine)
            .join(PharmacySaleItem.sale)
            .group_by(PharmacyMedicine.name)
            .order_by(desc(func.sum(PharmacySaleItem.quantity)))
            .limit(8)
        )
        if branch_id:
            stmt = stmt.where(PharmacySale.branch_id == branch_id)
        return [{"label": name, "value": float(value or 0)} for name, value in self.db.execute(stmt)]

    def _near_expiry(self, branch_id) -> int:
        until = date.today() + timedelta(days=45)
        pharmacy = select(func.count(PharmacyPurchase.id)).where(PharmacyPurchase.expiry_date <= until, PharmacyPurchase.expiry_date >= date.today())
        stock = select(func.count(StockBatch.id)).where(StockBatch.expiry_date <= until, StockBatch.expiry_date >= date.today())
        reagent = select(func.count(ReagentBatch.id)).where(ReagentBatch.expiry_date <= until, ReagentBatch.expiry_date >= date.today())
        if branch_id:
            pharmacy = pharmacy.where(PharmacyPurchase.branch_id == branch_id)
        return (self.db.scalar(pharmacy) or 0) + (self.db.scalar(stock) or 0) + (self.db.scalar(reagent) or 0)

    def _upcoming_appointments(self, branch_id) -> list[dict]:
        stmt = select(Appointment).where(Appointment.appointment_at >= datetime.now(UTC)).order_by(Appointment.appointment_at).limit(6)
        if branch_id:
            stmt = stmt.where(Appointment.branch_id == branch_id)
        return [
            {
                "label": item.patient.first_name + " " + item.patient.last_name if item.patient else item.appointment_number,
                "time": item.appointment_at.isoformat(),
                "status": item.status,
            }
            for item in self.db.scalars(stmt)
        ]

    def _activity_feed(self, branch_id) -> list[dict]:
        rows: list[dict] = []
        for item in self.db.scalars(self._branch(select(Patient).order_by(Patient.created_at.desc()).limit(4), Patient, branch_id)):
            rows.append({"time": item.created_at.isoformat(), "module": "Patients", "text": f"New patient registered: {item.patient_number}", "tone": "info"})
        for item in self.db.scalars(self._branch(select(BillingPayment).order_by(BillingPayment.received_at.desc()).limit(4), BillingPayment, branch_id)):
            rows.append({"time": item.received_at.isoformat(), "module": "Billing", "text": f"Payment collected {float(item.amount):,.0f} BDT", "tone": "good"})
        for item in self.db.scalars(self._branch(select(ERVisit).order_by(ERVisit.arrival_time.desc()).limit(4), ERVisit, branch_id)):
            rows.append({"time": item.arrival_time.isoformat(), "module": "Emergency", "text": f"ER arrival {item.visit_number} ({item.triage_category})", "tone": "warn"})
        for item in self.db.scalars(self._branch(select(HRPayrollRun).order_by(HRPayrollRun.created_at.desc()).limit(2), HRPayrollRun, branch_id)):
            rows.append({"time": item.created_at.isoformat(), "module": "HR", "text": f"Payroll {item.payroll_month} {item.status}", "tone": "info"})
        return sorted(rows, key=lambda row: row["time"], reverse=True)[:10]

    def _branch(self, stmt, model, branch_id):
        if branch_id and hasattr(model, "branch_id"):
            return stmt.where(model.branch_id == branch_id)
        return stmt

    def _alerts(self, **values) -> list[dict]:
        alerts = []
        if values["low_stock_meds"] or values["low_stock_items"]:
            alerts.append({"severity": "critical", "title": "Low stock", "message": f"{values['low_stock_meds']} medicines and {values['low_stock_items']} inventory items need reorder."})
        if values["lab_pending"] or values["radiology_pending"]:
            alerts.append({"severity": "warning", "title": "Pending reports", "message": f"{values['lab_pending']} lab and {values['radiology_pending']} radiology reports are pending."})
        if values["pending_bills"]:
            alerts.append({"severity": "warning", "title": "Outstanding billing", "message": f"{values['pending_bills']} invoices have dues worth BDT {values['unpaid_due']:,.0f}."})
        if values["occupancy_pct"] >= 85:
            alerts.append({"severity": "critical", "title": "High bed occupancy", "message": f"Current bed occupancy is {values['occupancy_pct']}%."})
        if values["emergency_today"] >= 5:
            alerts.append({"severity": "critical", "title": "Emergency load", "message": f"{values['emergency_today']} emergency arrivals today."})
        if values["absent_staff"] or values["leave_staff"]:
            alerts.append({"severity": "info", "title": "Staff coverage", "message": f"{values['absent_staff']} absent and {values['leave_staff']} on leave today."})
        if not alerts:
            alerts.append({"severity": "good", "title": "Stable operations", "message": "No major operational alert detected."})
        return alerts

    def _report_shortcuts(self) -> list[dict]:
        return [
            {"label": "Patient report", "route": "/patients"},
            {"label": "Appointment report", "route": "/appointments"},
            {"label": "Revenue report", "route": "/reporting"},
            {"label": "Admission report", "route": "/ipd"},
            {"label": "Bed report", "route": "/ipd"},
            {"label": "Emergency report", "route": "/er"},
            {"label": "Lab report", "route": "/laboratory"},
            {"label": "Pharmacy report", "route": "/pharmacy"},
            {"label": "Inventory report", "route": "/inventory"},
            {"label": "OT report", "route": "/ot"},
            {"label": "HR report", "route": "/hr/reports"},
            {"label": "Payroll report", "route": "/hr/payroll"},
        ]

    def _kpi(self, title: str, value, description: str, icon: str, tone: str, trend: float, *, money: bool = False) -> dict:
        return {
            "title": title,
            "value": float(value or 0) if money else int(value or 0),
            "description": description,
            "icon": icon,
            "tone": tone,
            "trend": trend,
            "format": "money" if money else "number",
            "sparkline": [max(0, int((value or 0) * factor / 10)) for factor in [4, 5, 4, 6, 7, 6, 9]],
        }
