export interface InvestigationWorkItem {
  order_id: string;
  visit_id: string;
  visit_number: string;
  visit_date: string;
  patient_id: string;
  patient_name: string;
  consulting_doctor_name: string;
  service_area: string;
  item_name: string;
  quantity: string;
  instructions?: string | null;
  status: string;
  result_text?: string | null;
  completed_at?: string | null;
}

export interface InvestigationResultPayload {
  status: string;
  result_text?: string | null;
}
