export interface QueueCounter {
  id: string;
  code: string;
  name: string;
  module: string;
  service_area?: string | null;
  department_name?: string | null;
  room_number?: string | null;
  doctor_user_id?: string | null;
  assigned_user_id?: string | null;
  status: string;
  audio_enabled: boolean;
  display_enabled: boolean;
  current_token_id?: string | null;
  settings?: Record<string, unknown>;
}

export interface QueueToken {
  id: string;
  token_number: string;
  token_sequence: number;
  token_date: string;
  queue_scope: string;
  module: string;
  service_area?: string | null;
  department_name?: string | null;
  doctor_user_id?: string | null;
  counter_id?: string | null;
  patient_id?: string | null;
  patient_label?: string | null;
  priority: string;
  status: string;
  source_type: string;
  source_id: string;
  visit_id?: string | null;
  appointment_id?: string | null;
  order_id?: string | null;
  invoice_id?: string | null;
  blood_request_id?: string | null;
  called_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  skipped_at?: string | null;
  recalled_at?: string | null;
  due_at?: string | null;
  notes?: string | null;
  meta?: Record<string, unknown>;
  created_at: string;
  waiting_minutes: number;
}

export interface QueueSummary {
  total_waiting: number;
  total_called: number;
  total_in_progress: number;
  total_completed: number;
  skipped_count: number;
  longest_wait_minutes: number;
  average_wait_minutes: number;
  by_scope: Record<string, number>;
  by_counter: Record<string, number>;
}

export interface QueueDisplay {
  scope: string;
  current: QueueToken[];
  next_tokens: QueueToken[];
  announcements: string[];
}

export interface QueueSetting {
  id: string;
  setting_key: string;
  setting_value: Record<string, unknown>;
}
