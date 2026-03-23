import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { CreatePatientPayload, Patient, PatientClinicalHistory } from '../models/patient.models';

@Injectable({ providedIn: 'root' })
export class PatientService extends ApiBaseService {
  list(): Observable<Patient[]> {
    return this.http.get<Patient[]>(this.url('/patients'));
  }

  get(patientId: string): Observable<Patient> {
    return this.http.get<Patient>(this.url(`/patients/${patientId}`));
  }

  getHistory(patientId: string): Observable<PatientClinicalHistory> {
    return this.http.get<PatientClinicalHistory>(this.url(`/patients/${patientId}/history`));
  }

  create(payload: CreatePatientPayload): Observable<Patient> {
    return this.http.post<Patient>(this.url('/patients'), payload);
  }
}
