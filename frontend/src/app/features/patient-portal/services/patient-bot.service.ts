import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { PatientAppointment } from '../models/patient-portal.models';
import { PatientBotConversation, PatientBotDoctorCard, PatientBotResponse, PatientBotSettings } from '../models/patient-bot.models';

@Injectable({ providedIn: 'root' })
export class PatientBotService extends ApiBaseService {
  sendMessage(message: string, conversationId?: string | null): Observable<PatientBotResponse> {
    return this.http.post<PatientBotResponse>(this.url('/patient-bot/message'), {
      message,
      conversation_id: conversationId || null,
    });
  }

  reset(): Observable<PatientBotResponse> {
    return this.http.post<PatientBotResponse>(this.url('/patient-bot/reset'), {});
  }

  listConversations(): Observable<PatientBotConversation[]> {
    return this.http.get<PatientBotConversation[]>(this.url('/patient-bot/conversations'));
  }

  getConversation(conversationId: string): Observable<PatientBotConversation> {
    return this.http.get<PatientBotConversation>(this.url(`/patient-bot/conversations/${conversationId}`));
  }

  suggestedDoctors(department?: string | null): Observable<PatientBotDoctorCard[]> {
    const suffix = department ? `?department=${encodeURIComponent(department)}` : '';
    return this.http.get<PatientBotDoctorCard[]>(this.url(`/patient-bot/suggested-doctors${suffix}`));
  }

  bookAppointment(payload: { conversation_id: string; doctor_user_id: string; appointment_at: string; reason: string }): Observable<PatientAppointment> {
    return this.http.post<PatientAppointment>(this.url('/patient-bot/book-appointment-request'), payload);
  }

  settings(): Observable<PatientBotSettings> {
    return this.http.get<PatientBotSettings>(this.url('/patient-bot/settings'));
  }
}
