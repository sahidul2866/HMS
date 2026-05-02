export interface PatientBotDoctorCard {
  id: string;
  name: string;
  department: string;
  specialty: string;
  qualification?: string | null;
  fee?: string | null;
  chamber?: string | null;
  available_today: boolean;
  languages: string[];
}

export interface PatientBotResponse {
  conversation_id: string;
  message: string;
  type: string;
  needs_more_input: boolean;
  recommended_department?: string | null;
  recommended_doctor_type?: string | null;
  safety_level: string;
  gemini_used: boolean;
  quick_replies: string[];
  doctor_cards: PatientBotDoctorCard[];
  context_summary: Record<string, unknown>;
  next_action?: string | null;
}

export interface PatientBotMessage {
  id: string;
  sender: string;
  message_type: string;
  content: string;
  payload: Record<string, unknown>;
  gemini_used: boolean;
  created_at: string;
}

export interface PatientBotConversation {
  id: string;
  title: string;
  current_intent?: string | null;
  state: string;
  intake: Record<string, unknown>;
  recommended_department?: string | null;
  recommended_doctor_type?: string | null;
  safety_level: string;
  created_at: string;
  updated_at: string;
  messages: PatientBotMessage[];
}

export interface PatientBotSettings {
  enabled: boolean;
  gemini_enabled: boolean;
  model_name: string;
  max_gemini_calls_per_patient_per_day: number;
  diet_guidance_enabled: boolean;
  report_explanation_enabled: boolean;
  prescription_explanation_enabled: boolean;
  appointment_booking_enabled: boolean;
  greeting_message: string;
  quick_replies: string[];
}
