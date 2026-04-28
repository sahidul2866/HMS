import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { OPDVisit } from '../../opd/models/opd.models';
import { Appointment, AppointmentCheckInPayload, AppointmentCreatePayload, AppointmentStatusPayload } from '../models/appointment.models';

@Injectable({ providedIn: 'root' })
export class AppointmentsService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  list(): Observable<Appointment[]> {
    return this.cache.get('appointments:list', () => this.http.get<Appointment[]>(this.url('/appointments')));
  }

  create(payload: AppointmentCreatePayload): Observable<Appointment> {
    return this.http.post<Appointment>(this.url('/appointments'), payload).pipe(tap(() => this.clearCache()));
  }

  updateStatus(appointmentId: string, payload: AppointmentStatusPayload): Observable<Appointment> {
    return this.http.put<Appointment>(this.url(`/appointments/${appointmentId}/status`), payload).pipe(tap(() => this.clearCache()));
  }

  checkIn(appointmentId: string, payload: AppointmentCheckInPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url(`/appointments/${appointmentId}/check-in`), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('appointments:');
    this.cache.clearPrefix('opd:');
  }
}
