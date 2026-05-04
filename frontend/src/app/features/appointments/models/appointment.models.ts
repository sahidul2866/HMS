export interface Appointment {
  id: string;
  appointment_number: string;
  patient_id: string;
  patient_name: string;
  doctor_user_id: string;
  doctor_name: string;
  appointment_at: string;
  slot_start_at?: string | null;
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
  appointment_at?: string | null;
  slot_start_at?: string | null;
  reason?: string | null;
  note?: string | null;
}

export interface AppointmentUpdatePayload {
  doctor_user_id: string;
  slot_start_at: string;
  reason?: string | null;
  note?: string | null;
}

export interface DoctorSlotAvailability {
  slot_start_at: string;
  slot_end_at: string;
  status: 'available' | 'booked' | 'in_progress' | string;
  source_type?: string | null;
}

export interface DoctorSlotsResponse {
  doctor_user_id: string;
  date: string;
  slot_duration_minutes: number;
  buffer_minutes: number;
  slots: DoctorSlotAvailability[];
}
