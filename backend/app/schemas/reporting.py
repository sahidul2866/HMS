from pydantic import BaseModel


class ClinicalOperationsSummaryRead(BaseModel):
    opd_visits: int
    opd_billed_visits: int
    opd_completed_visits: int
    scheduled_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    ipd_active_admissions: int
    ipd_total_admissions: int
    ipd_discharged_admissions: int
    pending_laboratory: int
    completed_laboratory: int
    verified_laboratory: int
    pending_radiology: int
    completed_radiology: int
    verified_radiology: int
    pending_prescriptions: int
    pharmacy_dispenses: int
    unpaid_invoices: int
    partial_invoices: int
    paid_invoices: int
    payment_receipts: int
    collected_amount: float
    outstanding_due_amount: float
    refunded_amount: float
