export interface OTDashboard {
  today_surgeries: number;
  upcoming_surgeries: number;
  ongoing_surgeries: number;
  completed_surgeries: number;
  cancelled_surgeries: number;
  emergency_surgeries: number;
  available_rooms: number;
  occupied_rooms: number;
  pending_pre_op: number;
  pending_anesthesia: number;
  surgeon_schedule: Record<string, number>;
  department_schedule: Record<string, number>;
  room_utilization: { room: string; status: string; procedure: string }[];
  alerts: string[];
}

export interface OTRoom {
  id: string;
  room_number: string;
  name: string;
  room_type: string;
  status: string;
  floor?: string | null;
  equipment_summary?: string | null;
  hourly_charge: string | number;
}

export interface OTBooking {
  id: string;
  booking_number: string;
  patient_id: string;
  patient_name?: string | null;
  patient_number?: string | null;
  procedure_name: string;
  surgery_type: string;
  priority_level: string;
  preferred_start_at: string;
  estimated_duration_minutes: number;
  department_name?: string | null;
  diagnosis?: string | null;
  status: string;
}

export interface OTSchedule {
  id: string;
  booking_id: string;
  room_id: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  status: string;
  booking_number?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
  procedure_name?: string | null;
  surgery_type?: string | null;
  priority_level?: string | null;
  department_name?: string | null;
  room_name?: string | null;
  room_number?: string | null;
  primary_surgeon_name?: string | null;
  anesthetist_name?: string | null;
}

export interface OTCaseSheet {
  schedule: OTSchedule;
  pre_op?: Record<string, unknown> | null;
  anesthesia?: Record<string, unknown> | null;
  surgery_note?: Record<string, unknown> | null;
  recovery?: Record<string, unknown> | null;
  consumables: Record<string, unknown>[];
  equipment: Record<string, unknown>[];
  billing: Record<string, unknown>[];
  documents: Record<string, unknown>[];
}
