import { Patient } from '../../patients/models/patient.models';

export interface ERSummary {
  total_visits: number;
  waiting_visits: number;
  triaged_visits: number;
  assigned_visits: number;
  in_treatment_visits: number;
  admitted_visits: number;
  discharged_visits: number;
  referred_visits: number;
}

export interface ERVisitAmbulance {
  id: string;
  ambulance_service: string;
  driver_name?: string | null;
  pickup_location?: string | null;
  drop_off_location?: string | null;
  received_at: string;
  note?: string | null;
  created_at: string;
}

export interface ERVisit {
  id: string;
  visit_number: string;
  patient: Patient;
  arrival_mode: string;
  arrival_time: string;
  source_reference?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  triage_category: string;
  triage_level: number;
  vitals?: string | null;
  chief_complaint?: string | null;
  initial_diagnosis?: string | null;
  preferred_doctor_user_id?: string | null;
  assigned_doctor_user_id?: string | null;
  assigned_nurse_user_id?: string | null;
  assigned_location?: string | null;
  treatment_status?: string | null;
  treatment_notes?: string | null;
  note?: string | null;
  disposition?: string | null;
  referral_hospital?: string | null;
  referral_doctor_name?: string | null;
  disposition_note?: string | null;
  status: string;
  admitted_to_ipd_admission_id?: string | null;
  discharged_at?: string | null;
  ambulance_records: ERVisitAmbulance[];
  created_at: string;
}

export interface CreateERVisitPayload {
  patient_id: string;
  arrival_mode: string;
  arrival_time: string;
  source_reference?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  triage_category: string;
  triage_level: number;
  chief_complaint?: string | null;
  initial_diagnosis?: string | null;
  preferred_doctor_user_id?: string | null;
  assigned_nurse_user_id?: string | null;
  assigned_location?: string | null;
  note?: string | null;
}

export interface ERVisitTriagePayload {
  triage_category: string;
  triage_level: number;
  vitals?: string | null;
  note?: string | null;
}

export interface ERVisitAssignmentPayload {
  assigned_doctor_user_id?: string | null;
  assigned_nurse_user_id?: string | null;
  assigned_location?: string | null;
  note?: string | null;
}

export interface ERVisitTreatmentPayload {
  treatment_status: string;
  treatment_notes?: string | null;
  disposition?: string | null;
  referral_hospital?: string | null;
  referral_doctor_name?: string | null;
  disposition_note?: string | null;
}

export interface ERVisitStatusPayload {
  status: string;
  note?: string | null;
}

export interface ERVisitAmbulancePayload {
  ambulance_service: string;
  driver_name?: string | null;
  pickup_location?: string | null;
  drop_off_location?: string | null;
  received_at: string;
  note?: string | null;
}

export interface ERConvertToIPDPayload {
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
