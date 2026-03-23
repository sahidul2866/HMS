from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.reporting.repository import ReportingRepository
from app.schemas.reporting import ClinicalOperationsSummaryRead


class ReportingService:
    def __init__(self, db: Session) -> None:
        self.repository = ReportingRepository(db)

    def get_clinical_summary(self, actor: User) -> ClinicalOperationsSummaryRead:
        data = self.repository.get_clinical_summary(actor.branch_id)
        return ClinicalOperationsSummaryRead(**data)
