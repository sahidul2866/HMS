export interface ClinicalOperationsSummary {
  opd_visits: number;
  ipd_active_admissions: number;
  ipd_total_admissions: number;
  pending_laboratory: number;
  completed_laboratory: number;
  pending_radiology: number;
  completed_radiology: number;
  pending_prescriptions: number;
  pharmacy_dispenses: number;
}
