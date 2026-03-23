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
}

export interface PatientHistoryBillingInvoice {
  id: string;
  invoice_number: string;
  created_at: string;
  status: string;
  total_amount: string;
  referred_doctor_name?: string | null;
}

export interface PatientHistoryPharmacyDispense {
  id: string;
  prescription_ref?: string | null;
  medicine_name: string;
  quantity: string;
  total_price: string;
  created_at: string;
}

export interface PatientClinicalHistory {
  patient: Patient;
  opd_visits: PatientHistoryOPDVisit[];
  ipd_admissions: PatientHistoryIPDAdmission[];
  billing_invoices: PatientHistoryBillingInvoice[];
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
