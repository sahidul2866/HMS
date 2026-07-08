export interface OutpatientDashboard {
  opd_waiting: number;
  telemedicine_waiting: number;
  called: number;
  in_consultation: number;
  completed_today: number;
  no_show: number;
  pending_payments: number;
  pending_prescriptions: number;
  by_visit_type: Record<string, number>;
  by_status: Record<string, number>;
}

export interface UnifiedOutpatientQueueItem {
  token_id?: string | null;
  source_id: string;
  source_type: string;
  visit_mode: string;
  visit_type?: string | null;
  number: string;
  queue_number?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  doctor_user_id?: string | null;
  doctor_name?: string | null;
  department_name?: string | null;
  appointment_at?: string | null;
  status: string;
  queue_status?: string | null;
  payment_status?: string | null;
  waiting_minutes: number;
  priority: string;
  join_url?: string | null;
  current_complaint?: string | null;
  has_video_panel: boolean;
  meta: Record<string, unknown>;
}

export interface OutpatientReport {
  report_type: string;
  filters: Record<string, unknown>;
  rows: Array<Record<string, unknown>>;
  totals: Record<string, unknown>;
}
