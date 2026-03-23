import { Patient } from '../../patients/models/patient.models';

export interface IPDSummary {
  total_admissions: number;
  active_admissions: number;
  discharged_admissions: number;
  occupied_beds: number;
}

export interface IPDAdmission {
  id: string;
  bed_id?: string | null;
  doctor_user_id?: string | null;
  attending_doctor_user_id?: string | null;
  admission_number: string;
  admitted_at: string;
  admission_type: string;
  ward_name: string;
  bed_number: string;
  attending_doctor_name: string;
  diagnosis?: string | null;
  daily_charge: number;
  advance_amount: number;
  status: string;
  expected_discharge_date?: string | null;
  discharged_at?: string | null;
  discharge_note?: string | null;
  patient: Patient;
  created_at: string;
}

export interface IPDBed {
  id: string;
  ward_name: string;
  bed_number: string;
  bed_type: string;
  daily_rate: number;
  status: string;
  note?: string | null;
}

export interface CreateIPDAdmissionPayload {
  patient_id: string;
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

export interface CreateIPDBedPayload {
  ward_name: string;
  bed_number: string;
  bed_type: string;
  daily_rate: number;
  note?: string | null;
}
