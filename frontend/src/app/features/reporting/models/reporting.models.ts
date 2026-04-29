export interface ClinicalOperationsSummary {
  opd_visits: number;
  opd_billed_visits: number;
  opd_completed_visits: number;
  scheduled_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  ipd_active_admissions: number;
  ipd_total_admissions: number;
  ipd_discharged_admissions: number;
  pending_laboratory: number;
  completed_laboratory: number;
  verified_laboratory: number;
  pending_radiology: number;
  completed_radiology: number;
  verified_radiology: number;
  pending_prescriptions: number;
  pharmacy_dispenses: number;
  unpaid_invoices: number;
  partial_invoices: number;
  paid_invoices: number;
  payment_receipts: number;
  collected_amount: number;
  outstanding_due_amount: number;
  refunded_amount: number;
}

export interface ReportCatalogItem {
  category: string;
  name: string;
  route: string;
  description: string;
  permission: string;
}

export interface ReportCatalog {
  categories: string[];
  reports: ReportCatalogItem[];
}
