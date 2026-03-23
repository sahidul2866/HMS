import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { PatientAppointment, PatientAppointmentPayload, PatientPortalOverview } from '../models/patient-portal.models';

@Injectable({ providedIn: 'root' })
export class PatientPortalService extends ApiBaseService {
  getOverview(): Observable<PatientPortalOverview> {
    return this.http.get<PatientPortalOverview>(this.url('/portal/overview'));
  }

  listAppointments(): Observable<PatientAppointment[]> {
    return this.http.get<PatientAppointment[]>(this.url('/portal/appointments'));
  }

  bookAppointment(payload: PatientAppointmentPayload): Observable<PatientAppointment> {
    return this.http.post<PatientAppointment>(this.url('/portal/appointments'), payload);
  }
}
