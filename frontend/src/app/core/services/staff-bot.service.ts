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
}

export interface StaffBotSettings {
  greeting_message: string;
  quick_actions: string[];
  gemini_enabled: boolean;
}

@Injectable({ providedIn: 'root' })
export class StaffBotService extends ApiBaseService {
  settings(): Observable<StaffBotSettings> {
    return this.http.get<StaffBotSettings>(this.url('/staff-bot/settings'));
  }

  sendMessage(payload: { message: string; conversation_id?: string | null; context?: string | null }): Observable<StaffBotResponse> {
    return this.http.post<StaffBotResponse>(this.url('/staff-bot/message'), {
      message: payload.message,
      conversation_id: payload.conversation_id || null,
      context: payload.context || null,
    });
  }

  reset(payload?: { context?: string | null }): Observable<StaffBotResponse> {
    return this.http.post<StaffBotResponse>(this.url('/staff-bot/reset'), { context: payload?.context || null });
  }
}
