from pydantic import BaseModel


class ClinicalOperationsSummaryRead(BaseModel):
    opd_visits: int
    ipd_active_admissions: int
    ipd_total_admissions: int
    pending_laboratory: int
    completed_laboratory: int
    pending_radiology: int
    completed_radiology: int
    pending_prescriptions: int
    pharmacy_dispenses: int
