export interface Appointment {
  id: string;
  appointment_number: string;
  patient_id: string;
  patient_name: string;
  doctor_user_id: string;
  doctor_name: string;
  appointment_at: string;
  status: string;
  reason?: string | null;
  note?: string | null;
}

export interface AppointmentStatusPayload {
  status: string;
}

export interface AppointmentCheckInPayload {
  department_name: string;
  consultation_fee: number;
  chief_complaint?: string | null;
  note?: string | null;
}

export interface AppointmentCreatePayload {
  patient_id: string;
  doctor_user_id: string;
  appointment_at: string;
  reason?: string | null;
  note?: string | null;
}
