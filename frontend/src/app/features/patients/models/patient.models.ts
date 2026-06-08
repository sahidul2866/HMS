export interface Patient {
  id: string;
  patient_number: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  email?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
}

export interface PatientIdCardTemplate {
  card_size: string;
  logo_url?: string | null;
  header: string;
  footer: string;
  code_type: string;
  theme_color: string;
  show_phone: boolean;
  show_emergency_contact: boolean;
  show_dob: boolean;
  show_issue_date: boolean;
  print_layout: string;
}

export interface PatientIdCard {
  patient: Patient;
  hospital_name: string;
  scan_code: string;
  code_type: string;
  issue_date: string;
  is_reprint: boolean;
  template: PatientIdCardTemplate;
}

export interface PatientLookupResult extends Patient {
  full_name: string;
}

export interface PatientMobileLookup {
  mobile: string;
  normalized_mobile: string;
  max_patients_allowed: number;
  current_patient_count: number;
  can_add_more: boolean;
  patients: PatientLookupResult[];
}

export interface PatientHistoryOrder {
  id: string;
  order_type: string;
  service_area?: string | null;
  item_name: string;
  quantity: string;
  status: string;
  instructions?: string | null;
  result_text?: string | null;
  completed_at?: string | null;
}

export interface PatientHistoryOPDVisit {
  id: string;
  visit_number: string;
  visit_date: string;
  department_name: string;
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
  note?: string | null;
  status: string;
  orders: PatientHistoryOrder[];
}

export interface PatientHistoryIPDAdmission {
  id: string;
  admission_number: string;
  admitted_at: string;
  attending_doctor_name: string;
  diagnosis?: string | null;
  status: string;
  ward_name: string;
  bed_number: string;
  discharged_at?: string | null;
  active_doctors?: string[];
  active_nurses?: string[];
  tracking?: Array<{ title: string; detail?: string | null; time?: string | null; type?: string | null }>;
}

export interface PatientHistoryBillingInvoice {
  id: string;
  invoice_number: string;
  created_at: string;
  status: string;
  payment_status: string;
  total_amount: string;
  paid_amount: string;
  due_amount: string;
  referred_doctor_name?: string | null;
}

export interface PatientHistoryBillingPayment {
  id: string;
  invoice_number: string;
  receipt_number: string;
  payment_method: string;
  amount: string;
  received_at: string;
  note?: string | null;
}

export interface PatientHistoryPharmacyDispense {
  id: string;
  prescription_ref?: string | null;
  medicine_name: string;
  quantity: string;
  total_price: string;
  created_at: string;
}

export interface PatientHistoryAppointment {
  id: string;
  appointment_number: string;
  doctor_name: string;
  appointment_at: string;
  status: string;
  reason?: string | null;
  note?: string | null;
}

export interface PatientClinicalHistory {
  patient: Patient;
  opd_visits: PatientHistoryOPDVisit[];
  appointments: PatientHistoryAppointment[];
  ipd_admissions: PatientHistoryIPDAdmission[];
  billing_invoices: PatientHistoryBillingInvoice[];
  billing_payments: PatientHistoryBillingPayment[];
  pharmacy_dispenses: PatientHistoryPharmacyDispense[];
}

export interface CreatePatientPayload {
  branch_id?: string | null;
  first_name: string;
  last_name: string;
  phone?: string | null;
  email?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
}
