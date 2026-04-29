from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.reporting.repository import ReportingRepository
from app.schemas.reporting import (
    AppointmentSummaryRead,
    ClinicalOperationsSummaryRead,
    FinancialSummaryRead,
    LabRadiologySummaryRead,
    PharmacySummaryRead,
    RevenueSummaryRead,
    DashboardAnalyticsRead,
    ReportCatalogRead,
)


class ReportingService:
    def __init__(self, db: Session) -> None:
        self.repository = ReportingRepository(db)

    def get_clinical_summary(self, actor: User) -> ClinicalOperationsSummaryRead:
        data = self.repository.get_clinical_summary(actor.branch_id)
        return ClinicalOperationsSummaryRead(**data)

    def get_financial_summary(self, actor: User) -> FinancialSummaryRead:
        data = self.repository.get_financial_summary(actor.branch_id)
        return FinancialSummaryRead(**data)

    def get_appointment_summary(self, actor: User) -> AppointmentSummaryRead:
        data = self.repository.get_appointment_summary(actor.branch_id)
        return AppointmentSummaryRead(**data)

    def get_lab_radiology_summary(self, actor: User) -> LabRadiologySummaryRead:
        data = self.repository.get_lab_radiology_summary(actor.branch_id)
        return LabRadiologySummaryRead(**data)

    def get_pharmacy_summary(self, actor: User) -> PharmacySummaryRead:
        data = self.repository.get_pharmacy_summary(actor.branch_id)
        return PharmacySummaryRead(**data)

    def get_revenue_summary(self, actor: User) -> RevenueSummaryRead:
        data = self.repository.get_revenue_summary(actor.branch_id)
        return RevenueSummaryRead(**data)

    def get_dashboard_analytics(
        self,
        actor: User,
        *,
        date_from=None,
        date_to=None,
        department: str | None = None,
        doctor_id: str | None = None,
        patient_type: str | None = None,
        payment_status: str | None = None,
        module_type: str | None = None,
    ) -> DashboardAnalyticsRead:
        data = self.repository.get_dashboard_analytics(
            actor.branch_id,
            date_from=date_from,
            date_to=date_to,
            department=department,
            doctor_id=doctor_id,
            patient_type=patient_type,
            payment_status=payment_status,
            module_type=module_type,
        )
        return DashboardAnalyticsRead(**data)

    def get_report_catalog(self, actor: User) -> ReportCatalogRead:
        categories: dict[str, list[str]] = {
            "Accounting & Finance": ["Daily Collection", "Monthly Collection", "Revenue", "Expense", "Profit & Loss", "Cash Flow", "Balance Sheet", "Department Revenue", "Service Revenue", "Doctor Revenue", "Patient Due", "Due Aging", "Insurance Receivable", "Corporate Receivable", "Supplier Payable", "Supplier Aging", "Refund", "Discount", "Cashier Collection", "Cash Closing", "Bank Reconciliation", "Payment Method", "Payroll Cost", "Doctor Commission", "Tax/VAT"],
            "Patient": ["Total Patient", "New Patient", "Returning Patient", "OPD Patient", "IPD Patient", "Emergency Patient", "Department Patient", "Doctor Patient", "Visit History", "Demographic", "Registration Trend"],
            "Appointment": ["Daily Appointment", "Doctor Appointment", "Department Appointment", "Completed Appointment", "Cancelled Appointment", "No-show", "Appointment Trend"],
            "Admission & Bed": ["Admission", "Discharge", "Current Admitted", "Bed Occupancy", "Ward Bed", "ICU/CCU/NICU Bed", "Average Length of Stay", "Bed Utilization"],
            "Emergency": ["Daily Emergency", "Case Type", "Triage Priority", "Critical Patient", "Waiting Time", "Admission vs Discharge", "Ambulance Arrival"],
            "OT / Surgery": ["Daily Surgery", "Monthly Surgery", "Surgeon Surgery", "Department Surgery", "OT Room Utilization", "Surgery Cancellation", "Surgery Delay", "OT Revenue", "OT Consumable Usage", "Anesthesia"],
            "Lab & Radiology": ["Lab Test", "Pending Lab", "Completed Lab", "Test Volume", "Department Lab Order", "Lab Revenue", "Radiology Order", "Radiology Revenue", "Turnaround Time"],
            "Pharmacy": ["Pharmacy Sales", "Medicine Sales", "Top Selling Medicine", "Medicine Return", "Expired Medicine", "Low Stock Medicine", "Pharmacy Profit", "Prescription Sale"],
            "Inventory": ["Current Stock", "Low Stock", "Out of Stock", "Near Expiry", "Expired Stock", "Stock Movement", "Stock Receive", "Stock Issue", "Department Consumption", "Supplier Purchase", "Inventory Valuation", "Reagent Stock", "Reagent Usage", "Reagent Wastage", "Reagent Expiry"],
            "HR & Payroll": ["Employee List", "Department Employee", "Attendance", "Late Attendance", "Absence", "Leave", "Shift Roster", "Payroll Summary", "Payslip", "Overtime", "Loan/Advance", "Resigned Employee", "Staff Duty"],
            "Management Summary": ["Executive Dashboard", "Daily Hospital Summary", "Monthly Hospital Summary", "Revenue vs Expense", "Department Performance", "Doctor Performance", "Operational Efficiency", "Top Services", "High Due Patients", "High Revenue Patients", "Hospital Growth Trend"],
        }
        reports = []
        for category, names in categories.items():
            for name in names:
                slug = name.lower().replace("/", "").replace(" ", "-")
                reports.append({"category": category, "name": f"{name} Report", "route": "/reporting", "description": f"{category} report with filters, summary cards, print and export actions.", "permission": "reporting.view"})
        return ReportCatalogRead(categories=list(categories), reports=reports)
