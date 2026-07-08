export interface TelemedicineDashboard {
  todays_online_appointments: number;
  waiting_patients: number;
  active_consultations: number;
  completed_consultations: number;
  missed_no_show: number;
  pending_payments: number;
  pending_prescriptions: number;
  follow_up_requests: number;
  doctors_available: number;
  by_status: Record<string, number>;
  by_payment_status: Record<string, number>;
}

export interface TelemedicineAppointment {
  id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_number?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  doctor_user_id: string;
  doctor_name?: string | null;
  telemedicine_number: string;
  appointment_at: string;
  consultation_reason?: string | null;
  visit_type: string;
  appointment_type: string;
  contact_phone?: string | null;
  contact_email?: string | null;
  uploaded_files: Array<Record<string, unknown>>;
  queue_number?: string | null;
  estimated_wait_minutes?: number | null;
  status: string;
  payment_status: string;
  consultation_fee: string | number;
  billing_invoice_id?: string | null;
  consent_required: boolean;
  consent_accepted: boolean;
  consent_at?: string | null;
  consent_by?: string | null;
  video_provider?: string | null;
  meeting_id?: string | null;
  join_url?: string | null;
  doctor_join_url?: string | null;
  remarks?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface TelemedicineConsultation {
  id: string;
  telemedicine_appointment_id: string;
  telemedicine_number?: string | null;
  patient_id: string;
  patient_name?: string | null;
  patient_number?: string | null;
  doctor_user_id: string;
  doctor_name?: string | null;
  opd_visit_id?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  patient_joined_at?: string | null;
  doctor_joined_at?: string | null;
  connection_status: string;
  media_status?: Record<string, unknown> | null;
  current_complaint?: string | null;
  notes?: string | null;
  diagnosis?: string | null;
  prescription_text?: string | null;
  advice?: string | null;
  follow_up_date?: string | null;
  follow_up_plan?: string | null;
  referral_department?: string | null;
  status: string;
  prescription_status: string;
  completed_by_name?: string | null;
  completed_at?: string | null;
  remarks?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface TelemedicineChatMessage {
  id: string;
  consultation_id: string;
  sender_name?: string | null;
  sender_role: string;
  message: string;
  message_type: string;
  attachment_id?: string | null;
  read_at?: string | null;
  created_at: string;
}

export interface TelemedicineFile {
  id: string;
  telemedicine_appointment_id?: string | null;
  consultation_id?: string | null;
  patient_id: string;
  uploaded_by_name?: string | null;
  file_category: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  file_url: string;
  validation_status: string;
  remarks?: string | null;
  created_at: string;
}

export interface TelemedicineSetting {
  id: string;
  setting_key: string;
  setting_value: string;
  description?: string | null;
  meta?: Record<string, unknown> | null;
  is_active: boolean;
}

export interface TelemedicineReport {
  report_type: string;
  filters: Record<string, unknown>;
  rows: Array<Record<string, unknown>>;
  totals: Record<string, unknown>;
}
