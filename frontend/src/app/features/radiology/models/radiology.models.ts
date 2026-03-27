export interface InvestigationWorkItem {
  order_id: string;
  visit_id: string;
  visit_number: string;
  visit_date: string;
  patient_id: string;
  patient_number: string;
  patient_name: string;
  consulting_doctor_name: string;
  service_area: string;
  item_name: string;
  quantity: string;
  instructions?: string | null;
  chief_complaint?: string | null;
  diagnosis?: string | null;
  status: string;
  sample_note?: string | null;
  sample_collected_at?: string | null;
  result_text?: string | null;
  completed_at?: string | null;
  verified_at?: string | null;
}

export interface InvestigationResultPayload {
  status: string;
  sample_note?: string | null;
  result_text?: string | null;
}

export interface RadiologySummary {
  total_orders: number;
  pending_orders: number;
  ready_orders: number;
  in_progress_orders: number;
  completed_orders: number;
  verified_orders: number;
}
