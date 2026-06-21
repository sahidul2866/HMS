import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  PatientAppointment,
  PatientAppointmentPayload,
  PatientAppointmentStatusPayload,
  PatientPortalOverview,
} from '../models/patient-portal.models';
import { DoctorSlotsResponse } from '../../appointments/models/appointment.models';

@Injectable({ providedIn: 'root' })
export class PatientPortalService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getOverview(): Observable<PatientPortalOverview> {
    return this.cache.get('portal:overview', () => this.http.get<PatientPortalOverview>(this.url('/portal/overview')));
  }

  listAppointments(): Observable<PatientAppointment[]> {
    return this.cache.get('portal:appointments', () => this.http.get<PatientAppointment[]>(this.url('/portal/appointments')));
  }

  bookAppointment(payload: PatientAppointmentPayload): Observable<PatientAppointment> {
    return this.http.post<PatientAppointment>(this.url('/portal/appointments'), payload).pipe(tap(() => this.clearCache()));
  }

  getDoctorSlots(doctorUserId: string, slotDate: string): Observable<DoctorSlotsResponse> {
    const params = `doctor_user_id=${encodeURIComponent(doctorUserId)}&slot_date=${encodeURIComponent(slotDate)}`;
    return this.http.get<DoctorSlotsResponse>(this.url(`/portal/doctor-slots?${params}`));
  }

  updateAppointmentStatus(appointmentId: string, payload: PatientAppointmentStatusPayload): Observable<PatientAppointment> {
    return this.http.put<PatientAppointment>(this.url(`/portal/appointments/${appointmentId}/status`), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('portal:');
  }
}
