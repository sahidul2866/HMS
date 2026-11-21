import { Patient } from '../../patients/models/patient.models';

export interface OPDDoctorLoad {
  doctor_user_id: string;
  doctor_name: string;
  visits: number;
}

export interface OPDLiveQueueItem {
  visit_id: string;
  queue_number?: string | null;
  patient_name: string;
  patient_number?: string | null;
  doctor_name?: string | null;
  status: string;
  payment_status: string;
  waiting_minutes: number;
  next_action: string;
}

/** One hospital day of OPD figures; money comes from that day's invoices. */
export interface OPDSummary {
  total_visits: number;
  waiting_visits: number;
  in_consultation_visits: number;
  completed_visits: number;
  summary_date?: string | null;
  as_of?: string | null;
  prescribed_visits?: number;
  cancelled_visits?: number;
  not_billed_visits?: number;
  paid_visits?: number;
  visits_with_balance?: number;
  gross_amount?: string;
  discount_amount?: string;
  billed_amount?: string;
  collected_amount?: string;
  outstanding_amount?: string;
  prescription_orders?: number;
  investigation_orders?: number;
  procedure_orders?: number;
  unassigned_visits?: number;
  doctor_load?: OPDDoctorLoad[];
  daily_visits?: Array<{ day: string; visits: number }>;
  live_queue?: OPDLiveQueueItem[];
}

export interface OPDVisitOrder {
  version?: number;
  prescription_detail?: Record<string,any>;
  id: string;
  order_type: string;
  service_area?: string | null;
  item_name: string;
  instructions?: string | null;
  quantity: number;
  status: string;
  result_text?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface OPDVisit {
  prescription_data?: Record<string,any> | null;
  prescription_template_id?: string | null;
  clinical_version?: number;
  prescription_status?: string;
  consultation_payment_source?: string;
  signed_prescription?: Record<string,any> | null;
  id: string;
  visit_number: string;
  visit_date: string;
  slot_start_at?: string | null;
  department_name: string;
  doctor_user_id?: string | null;
  consulting_doctor_user_id?: string | null;
  consulting_doctor_name: string;
  visit_type: string;
  chief_complaint?: string | null;
  history_of_present_illness?: string | null;
  past_history?: string | null;
  vital_signs?: string | null;
  examination_note?: string | null;
  provisional_diagnosis?: string | null;
  final_diagnosis?: string | null;
  follow_up_date?: string | null;
  follow_up_note?: string | null;
  status: string;
  queue_number?: string | null;
  queue_status?: string | null;
  queue_called_at?: string | null;
  converted_ipd_admission_id?: string | null;
  consultation_fee: number;
  consultation_discount?: number;
  consultation_total?: number;
  consultation_payment_status?: string;
  consultation_paid_at?: string | null;
  note?: string | null;
  patient: Patient;
  orders: OPDVisitOrder[];
  created_at: string;
}

export interface CreateOPDVisitPayload {
  patient_id: string;
  visit_date: string;
  slot_start_at?: string | null;
  department_name: string;
  doctor_user_id?: string | null;
  consulting_doctor_name: string;
  consultation_fee: number;
  visit_type: string;
  chief_complaint?: string | null;
  note?: string | null;
}

export interface UpdateOPDConsultationPayload {
  expected_version?: number;
  prescription_data?: Record<string,any>;
  prescription_template_id?: string | null;
  chief_complaint?: string | null;
  history_of_present_illness?: string | null;
  past_history?: string | null;
  vital_signs?: string | null;
  examination_note?: string | null;
  provisional_diagnosis?: string | null;
  final_diagnosis?: string | null;
  follow_up_date?: string | null;
  follow_up_note?: string | null;
  note?: string | null;
}

export interface CreateOPDVisitOrderPayload {
  request_key?: string;
  prescription_detail?: Record<string,unknown>;
  order_type: string;
  service_area?: string | null;
  item_name: string;
  instructions?: string | null;
  quantity: number;
}

export interface UpdateOPDVisitOrderPayload {
  expected_version?: number;
  service_area?: string | null;
  item_name?: string | null;
  room_number?: string | null;
  instructions?: string | null;
  quantity?: number | null;
  status?: string | null;
  result_text?: string | null;
  sample_note?: string | null;
}

export interface UpdateOPDVisitPayload {
  visit_date: string;
  department_name: string;
  doctor_user_id?: string | null;
  consulting_doctor_name: string;
  chief_complaint?: string | null;
  consultation_fee: number;
  note?: string | null;
}

export interface UpdateOPDPaymentPayload {
  amount: number;
  discount: number;
}

export interface ConvertOPDToIPDPayload {
  bed_id?: string | null;
  admitted_at: string;
  admission_type: string;
  department_name?: string | null;
  patient_condition?: string | null;
  ward_name: string;
  bed_number: string;
  doctor_user_id?: string | null;
  attending_doctor_name: string;
  diagnosis?: string | null;
  daily_charge: number;
  advance_amount: number;
  expected_discharge_date?: string | null;
}
