import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { OPDVisit } from '../../opd/models/opd.models';
import {
  Appointment,
  AppointmentCheckInPayload,
  AppointmentCreatePayload,
  AppointmentStatusPayload,
  AppointmentUpdatePayload,
  DoctorSlotsResponse,
} from '../models/appointment.models';

@Injectable({ providedIn: 'root' })
export class AppointmentsService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  list(): Observable<Appointment[]> {
    return this.cache.get('appointments:list', () => this.http.get<Appointment[]>(this.url('/appointments')));
  }

  create(payload: AppointmentCreatePayload): Observable<Appointment> {
    return this.http.post<Appointment>(this.url('/appointments'), payload).pipe(tap(() => this.clearCache()));
  }

  update(appointmentId: string, payload: AppointmentUpdatePayload): Observable<Appointment> {
    return this.http.put<Appointment>(this.url(`/appointments/${appointmentId}`), payload).pipe(tap(() => this.clearCache()));
  }

  updateStatus(appointmentId: string, payload: AppointmentStatusPayload): Observable<Appointment> {
    return this.http.put<Appointment>(this.url(`/appointments/${appointmentId}/status`), payload).pipe(tap(() => this.clearCache()));
  }

  checkIn(appointmentId: string, payload: AppointmentCheckInPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url(`/appointments/${appointmentId}/check-in`), payload).pipe(tap(() => this.clearCache()));
  }

  getDoctorSlots(doctorUserId: string, slotDate: string): Observable<DoctorSlotsResponse> {
    const params = `doctor_user_id=${encodeURIComponent(doctorUserId)}&slot_date=${encodeURIComponent(slotDate)}`;
    return this.cache.get(`appointments:slots:${doctorUserId}:${slotDate}`, () =>
      this.http.get<DoctorSlotsResponse>(this.url(`/appointments/doctor-slots?${params}`))
    );
  }

  listDoctorSchedules(doctorUserId?: string): Observable<Array<{
    id: string;
    doctor_user_id: string;
    weekday: number;
    start_time: string;
    end_time: string;
    slot_duration_minutes: number;
    buffer_minutes: number;
  }>> {
    const params = doctorUserId ? `?doctor_user_id=${encodeURIComponent(doctorUserId)}` : '';
    return this.http.get<Array<{
      id: string;
      doctor_user_id: string;
      weekday: number;
      start_time: string;
      end_time: string;
      slot_duration_minutes: number;
      buffer_minutes: number;
    }>>(this.url(`/appointments/doctor-schedules${params}`));
  }

  upsertDoctorSchedule(payload: {
    doctor_user_id: string;
    weekday: number;
    start_time: string;
    end_time: string;
    slot_duration_minutes: number;
    buffer_minutes: number;
  }): Observable<{
    id: string;
    doctor_user_id: string;
    weekday: number;
    start_time: string;
    end_time: string;
    slot_duration_minutes: number;
    buffer_minutes: number;
  }> {
    return this.http.post<{
      id: string;
      doctor_user_id: string;
      weekday: number;
      start_time: string;
      end_time: string;
      slot_duration_minutes: number;
      buffer_minutes: number;
    }>(this.url('/appointments/doctor-schedules'), payload);
  }

  clearCache(): void {
    this.cache.clearPrefix('appointments:');
    this.cache.clearPrefix('opd:');
  }
}
