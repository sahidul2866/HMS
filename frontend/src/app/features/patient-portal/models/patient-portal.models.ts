import { User } from '../../../core/models/auth.models';
import { PatientClinicalHistory } from '../../patients/models/patient.models';

export interface PatientAppointment {
  id: string;
  appointment_number: string;
  doctor_user_id: string;
  doctor_name: string;
  appointment_at: string;
  status: string;
  reason?: string | null;
  note?: string | null;
}

export interface PatientPortalOverview {
  patient: PatientClinicalHistory;
  appointments: PatientAppointment[];
  doctors: User[];
}

export interface PatientAppointmentPayload {
  doctor_user_id: string;
  appointment_at: string;
  reason: string;
  note?: string | null;
}
