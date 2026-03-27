import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { OPDVisit } from '../../opd/models/opd.models';
import { Appointment, AppointmentCheckInPayload, AppointmentCreatePayload, AppointmentStatusPayload } from '../models/appointment.models';

@Injectable({ providedIn: 'root' })
export class AppointmentsService extends ApiBaseService {
  list(): Observable<Appointment[]> {
    return this.http.get<Appointment[]>(this.url('/appointments'));
  }

  create(payload: AppointmentCreatePayload): Observable<Appointment> {
    return this.http.post<Appointment>(this.url('/appointments'), payload);
  }

  updateStatus(appointmentId: string, payload: AppointmentStatusPayload): Observable<Appointment> {
    return this.http.put<Appointment>(this.url(`/appointments/${appointmentId}/status`), payload);
  }

  checkIn(appointmentId: string, payload: AppointmentCheckInPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url(`/appointments/${appointmentId}/check-in`), payload);
  }
}
