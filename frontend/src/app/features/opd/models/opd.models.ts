import { Patient } from '../../patients/models/patient.models';

export interface OPDSummary {
  total_visits: number;
  waiting_visits: number;
  in_consultation_visits: number;
  completed_visits: number;
}

export interface OPDVisitOrder {
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
  id: string;
  visit_number: string;
  visit_date: string;
  department_name: string;
  doctor_user_id?: string | null;
  consulting_doctor_user_id?: string | null;
  consulting_doctor_name: string;
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
  converted_ipd_admission_id?: string | null;
  consultation_fee: number;
  note?: string | null;
  patient: Patient;
  orders: OPDVisitOrder[];
  created_at: string;
}

export interface CreateOPDVisitPayload {
  patient_id: string;
  visit_date: string;
  department_name: string;
  doctor_user_id?: string | null;
  consulting_doctor_name: string;
  chief_complaint?: string | null;
  consultation_fee: number;
  note?: string | null;
}

export interface UpdateOPDConsultationPayload {
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
  order_type: string;
  service_area?: string | null;
  item_name: string;
  instructions?: string | null;
  quantity: number;
}

export interface UpdateOPDVisitOrderPayload {
  status: string;
  result_text?: string | null;
}

export interface ConvertOPDToIPDPayload {
  bed_id?: string | null;
  admitted_at: string;
  admission_type: string;
  ward_name: string;
  bed_number: string;
  doctor_user_id?: string | null;
  attending_doctor_name: string;
  diagnosis?: string | null;
  daily_charge: number;
  advance_amount: number;
  expected_discharge_date?: string | null;
}
