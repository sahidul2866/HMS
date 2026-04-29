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


class FinancialSummaryRead(BaseModel):
    total_invoices: int
    unpaid_invoices: int
    partial_invoices: int
    paid_invoices: int
    payment_receipts: int
    collected_amount: float
    outstanding_due_amount: float
    refunded_amount: float


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


class FinancialSummaryRead(BaseModel):
    total_invoices: int
    unpaid_invoices: int
    partial_invoices: int
    paid_invoices: int
    payment_receipts: int
    collected_amount: float
    outstanding_due_amount: float
    refunded_amount: float


class AppointmentSummaryRead(BaseModel):
    scheduled_appointments: int
    confirmed_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    total_appointments: int


class LabRadiologySummaryRead(BaseModel):
    pending_laboratory: int
    completed_laboratory: int
    verified_laboratory: int
    pending_radiology: int
    completed_radiology: int
    verified_radiology: int


class PharmacySummaryRead(BaseModel):
    total_pharmacy_dispenses: int


class RevenueSummaryRead(BaseModel):
    total_revenue: float
    collected_revenue: float
    outstanding_revenue: float


class DashboardAnalyticsRead(BaseModel):
    generated_at: str
    filters: dict
    kpis: list[dict]
    patient_analytics: dict
    appointment_analytics: dict
    bed_analytics: dict
    emergency_analytics: dict
    revenue_analytics: dict
    lab_radiology_analytics: dict
    pharmacy_inventory_analytics: dict
    ot_analytics: dict
    hr_analytics: dict
    alerts: list[dict]
    activity_feed: list[dict]
    report_shortcuts: list[dict]


class ReportCatalogItemRead(BaseModel):
    category: str
    name: str
    route: str
    description: str
    permission: str = "reporting.view"


class ReportCatalogRead(BaseModel):
    categories: list[str]
    reports: list[ReportCatalogItemRead]
