import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { OTBooking, OTCaseSheet, OTDashboard, OTRoom, OTSchedule } from '../models/ot.models';

@Injectable({ providedIn: 'root' })
export class OTService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  dashboard(): Observable<OTDashboard> {
    return this.cache.get('ot:dashboard', () => this.http.get<OTDashboard>(this.url('/ot/dashboard')));
  }

  listRooms(): Observable<OTRoom[]> {
    return this.cache.getPersistent('ot:rooms', () => this.http.get<OTRoom[]>(this.url('/ot/rooms')));
  }

  createRoom(payload: Record<string, unknown>): Observable<OTRoom> {
    return this.http.post<OTRoom>(this.url('/ot/rooms'), payload).pipe(tap(() => this.clear()));
  }

  listBookings(q = ''): Observable<OTBooking[]> {
    const query = q ? `?q=${encodeURIComponent(q)}` : '';
    return this.cache.get(`ot:bookings:${query}`, () => this.http.get<OTBooking[]>(this.url(`/ot/bookings${query}`)));
  }

  createBooking(payload: Record<string, unknown>): Observable<OTBooking> {
    return this.http.post<OTBooking>(this.url('/ot/bookings'), payload).pipe(tap(() => this.clear()));
  }

  listSchedules(day?: string, status?: string): Observable<OTSchedule[]> {
    const params = new URLSearchParams();
    if (day) params.set('day', day);
    if (status) params.set('status', status);
    const query = params.toString();
    return this.cache.get(`ot:schedules:${query}`, () => this.http.get<OTSchedule[]>(this.url(`/ot/schedules${query ? `?${query}` : ''}`)));
  }

  createSchedule(payload: Record<string, unknown>): Observable<OTSchedule> {
    return this.http.post<OTSchedule>(this.url('/ot/schedules'), payload).pipe(tap(() => this.clear()));
  }

  updateStatus(id: string, status: string, note = ''): Observable<OTSchedule> {
    return this.http.post<OTSchedule>(this.url(`/ot/schedules/${id}/status`), { status, note }).pipe(tap(() => this.clear()));
  }

  upsertPreOp(id: string, payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url(`/ot/schedules/${id}/pre-op`), payload).pipe(tap(() => this.clear()));
  }

  upsertAnesthesia(id: string, payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url(`/ot/schedules/${id}/anesthesia`), payload).pipe(tap(() => this.clear()));
  }

  upsertSurgeryNote(id: string, payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url(`/ot/schedules/${id}/surgery-note`), payload).pipe(tap(() => this.clear()));
  }

  upsertRecovery(id: string, payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url(`/ot/schedules/${id}/recovery`), payload).pipe(tap(() => this.clear()));
  }

  addConsumable(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/ot/consumables'), payload).pipe(tap(() => this.clear()));
  }

  addEquipment(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/ot/equipment'), payload).pipe(tap(() => this.clear()));
  }

  addBillingItem(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/ot/billing-items'), payload).pipe(tap(() => this.clear()));
  }

  addDocument(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/ot/documents'), payload).pipe(tap(() => this.clear()));
  }

  getCaseSheet(id: string): Observable<OTCaseSheet> {
    return this.cache.get(`ot:case:${id}`, () => this.http.get<OTCaseSheet>(this.url(`/ot/case-sheet/${id}`)));
  }

  clear(): void {
    this.cache.clearPrefix('ot:');
    this.cache.clearPrefix('dashboard:');
  }
}
