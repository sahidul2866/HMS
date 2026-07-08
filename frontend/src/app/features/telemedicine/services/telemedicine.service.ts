import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import {
  TelemedicineAppointment,
  TelemedicineChatMessage,
  TelemedicineConsultation,
  TelemedicineDashboard,
  TelemedicineFile,
  TelemedicineReport,
  TelemedicineSetting,
} from '../models/telemedicine.models';

@Injectable({ providedIn: 'root' })
export class TelemedicineService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  dashboard(params: Record<string, string | number | null | undefined> = {}): Observable<TelemedicineDashboard> {
    const query = this.query(params);
    return this.cache.get(`telemedicine:dashboard:${query}`, () => this.http.get<TelemedicineDashboard>(this.url(`/telemedicine/dashboard${query}`)));
  }

  listAppointments(params: Record<string, string | undefined> = {}): Observable<TelemedicineAppointment[]> {
    const query = this.query(params);
    return this.cache.get(`telemedicine:appointments:${query}`, () => this.http.get<TelemedicineAppointment[]>(this.url(`/telemedicine/appointments${query}`)));
  }

  createAppointment(payload: Partial<TelemedicineAppointment> | Record<string, unknown>): Observable<TelemedicineAppointment> {
    return this.http.post<TelemedicineAppointment>(this.url('/telemedicine/appointments'), payload).pipe(tap(() => this.publish()));
  }

  updateAppointmentStatus(id: string, payload: Record<string, unknown>): Observable<TelemedicineAppointment> {
    return this.http.patch<TelemedicineAppointment>(this.url(`/telemedicine/appointments/${id}/status`), payload).pipe(tap(() => this.publish()));
  }

  acceptConsent(id: string, payload: Record<string, unknown>): Observable<TelemedicineAppointment> {
    return this.http.post<TelemedicineAppointment>(this.url(`/telemedicine/appointments/${id}/consent`), payload).pipe(tap(() => this.publish()));
  }

  updatePayment(id: string, payload: Record<string, unknown>): Observable<TelemedicineAppointment> {
    return this.http.post<TelemedicineAppointment>(this.url(`/telemedicine/appointments/${id}/payment`), payload).pipe(tap(() => this.publish()));
  }

  startConsultation(id: string): Observable<TelemedicineConsultation> {
    return this.http.post<TelemedicineConsultation>(this.url(`/telemedicine/appointments/${id}/start`), {}).pipe(tap(() => this.publish()));
  }

  listConsultations(params: Record<string, string | undefined> = {}): Observable<TelemedicineConsultation[]> {
    const query = this.query(params);
    return this.cache.get(`telemedicine:consultations:${query}`, () => this.http.get<TelemedicineConsultation[]>(this.url(`/telemedicine/consultations${query}`)));
  }

  updateConsultation(id: string, payload: Record<string, unknown>): Observable<TelemedicineConsultation> {
    return this.http.put<TelemedicineConsultation>(this.url(`/telemedicine/consultations/${id}`), payload).pipe(tap(() => this.publish()));
  }

  completeConsultation(id: string, payload: Record<string, unknown>): Observable<TelemedicineConsultation> {
    return this.http.post<TelemedicineConsultation>(this.url(`/telemedicine/consultations/${id}/complete`), payload).pipe(tap(() => this.publish()));
  }

  listChat(id: string): Observable<TelemedicineChatMessage[]> {
    return this.http.get<TelemedicineChatMessage[]>(this.url(`/telemedicine/consultations/${id}/chat`));
  }

  addChat(id: string, payload: Record<string, unknown>): Observable<TelemedicineChatMessage> {
    return this.http.post<TelemedicineChatMessage>(this.url(`/telemedicine/consultations/${id}/chat`), payload);
  }

  addFile(payload: Partial<TelemedicineFile> | Record<string, unknown>): Observable<TelemedicineFile> {
    return this.http.post<TelemedicineFile>(this.url('/telemedicine/files'), payload).pipe(tap(() => this.publish()));
  }

  listFiles(params: Record<string, string | undefined> = {}): Observable<TelemedicineFile[]> {
    const query = this.query(params);
    return this.http.get<TelemedicineFile[]>(this.url(`/telemedicine/files${query}`));
  }

  createInvestigation(id: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/telemedicine/consultations/${id}/investigations`), payload).pipe(tap(() => this.publish()));
  }

  listSettings(): Observable<TelemedicineSetting[]> {
    return this.cache.getPersistent('telemedicine:settings', () => this.http.get<TelemedicineSetting[]>(this.url('/telemedicine/settings')));
  }

  upsertSetting(payload: Partial<TelemedicineSetting> | Record<string, unknown>): Observable<TelemedicineSetting> {
    return this.http.post<TelemedicineSetting>(this.url('/telemedicine/settings'), payload).pipe(tap(() => this.publish()));
  }

  report(params: Record<string, string | undefined>): Observable<TelemedicineReport> {
    const query = this.query(params);
    return this.http.get<TelemedicineReport>(this.url(`/telemedicine/reports${query}`));
  }

  clearCache(): void {
    this.cache.clearPrefix('telemedicine:');
  }

  private publish(): void {
    this.clearCache();
    this.dataSync.publish({
      name: 'data.updated',
      entityType: 'telemedicine',
      modules: ['telemedicine', 'patients', 'appointments', 'opd', 'billing', 'pharmacy', 'laboratory', 'radiology', 'notifications', 'dashboard'],
      cachePrefixes: ['telemedicine:', 'patients:', 'appointments:', 'opd:', 'billing:', 'pharmacy:', 'laboratory:', 'radiology:', 'notifications:', 'dashboard:'],
      message: 'Telemedicine updates are available.',
    });
  }

  private query(params: Record<string, string | number | boolean | null | undefined>): string {
    const urlParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') urlParams.set(key, String(value));
    }
    const query = urlParams.toString();
    return query ? `?${query}` : '';
  }
}
