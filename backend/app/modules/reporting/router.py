from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.reporting.service import ReportingService
from app.schemas.reporting import (
    AppointmentSummaryRead,
    ClinicalOperationsSummaryRead,
    FinancialSummaryRead,
    LabRadiologySummaryRead,
    PharmacySummaryRead,
    RevenueSummaryRead,
)

router = APIRouter(prefix="/reporting", tags=["Reporting"])


@router.get("/clinical-summary", response_model=ClinicalOperationsSummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_clinical_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> ClinicalOperationsSummaryRead:
    return ReportingService(db).get_clinical_summary(user)


@router.get("/financial-summary", response_model=FinancialSummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_financial_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> FinancialSummaryRead:
    return ReportingService(db).get_financial_summary(user)


@router.get("/appointment-summary", response_model=AppointmentSummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_appointment_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> AppointmentSummaryRead:
    return ReportingService(db).get_appointment_summary(user)


@router.get("/lab-radiology-summary", response_model=LabRadiologySummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_lab_radiology_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> LabRadiologySummaryRead:
    return ReportingService(db).get_lab_radiology_summary(user)


@router.get("/pharmacy-summary", response_model=PharmacySummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_pharmacy_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> PharmacySummaryRead:
    return ReportingService(db).get_pharmacy_summary(user)


@router.get("/revenue-summary", response_model=RevenueSummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_revenue_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> RevenueSummaryRead:
    return ReportingService(db).get_revenue_summary(user)
