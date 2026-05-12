import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from './api-base.service';

export interface StaffBotResponse {
  conversation_id: string;
  message: string;
  intent?: string;
  source_module?: string;
  used_database?: boolean;
  used_gemini?: boolean;
  details?: Array<{ label: string; value: string }>;
  next_action?: string | null;
  quick_replies?: string[];
  follow_up?: boolean;
  required_fields?: string[];
  permission_denied?: boolean;
  context_suggestions?: string[];
  context_summary?: string | null;
  draft_content?: string | null;
  disclaimer?: string | null;
  actions?: Array<{ label: string; action: string; sensitive?: boolean; payload?: unknown }>;
  requires_confirmation?: boolean;
  confirmation_token?: string | null;
}

export interface StaffBotSettings {
  greeting_message: string;
  quick_actions: string[];
  gemini_enabled: boolean;
  enabled?: boolean;
  module_availability?: Record<string, boolean>;
  role_rules?: Record<string, unknown>;
  action_rules?: Record<string, unknown>;
  audit_logging?: boolean;
}

export interface StaffBotAdminSetting {
  id: string;
  setting_key: string;
  setting_value: Record<string, unknown>;
}

export interface StaffBotContext {
  module?: string | null;
  page?: string | null;
  path?: string | null;
  record_type?: string | null;
  record_id?: string | null;
  selected_label?: string | null;
  patient_id?: string | null;
  employee_id?: string | null;
  invoice_id?: string | null;
  visit_id?: string | null;
  appointment_id?: string | null;
  order_id?: string | null;
  filters?: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class StaffBotService extends ApiBaseService {
  settings(): Observable<StaffBotSettings> {
    return this.http.get<StaffBotSettings>(this.url('/staff-bot/settings'));
  }

  sendMessage(payload: { message: string; conversation_id?: string | null; context?: StaffBotContext | string | null }): Observable<StaffBotResponse> {
    return this.http.post<StaffBotResponse>(this.url('/staff-bot/message'), {
      message: payload.message,
      conversation_id: payload.conversation_id || null,
      context: payload.context || null,
    });
  }

  reset(payload?: { context?: StaffBotContext | string | null }): Observable<StaffBotResponse> {
    return this.http.post<StaffBotResponse>(this.url('/staff-bot/reset'), { context: payload?.context || null });
  }

  listAdminSettings(): Observable<StaffBotAdminSetting[]> {
    return this.http.get<StaffBotAdminSetting[]>(this.url('/staff-bot/admin-settings'));
  }

  saveAdminSetting(payload: { setting_key: string; setting_value: Record<string, unknown> }): Observable<StaffBotAdminSetting> {
    return this.http.post<StaffBotAdminSetting>(this.url('/staff-bot/admin-settings'), payload);
  }
}
