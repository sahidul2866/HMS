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
