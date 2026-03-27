import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { CreatePatientPayload, Patient, PatientClinicalHistory, PatientLookupResult, PatientMobileLookup } from '../models/patient.models';

@Injectable({ providedIn: 'root' })
export class PatientService extends ApiBaseService {
  list(): Observable<Patient[]> {
    return this.http.get<Patient[]>(this.url('/patients'));
  }

  search(q: string, limit = 10): Observable<PatientLookupResult[]> {
    const params = new URLSearchParams({ q, limit: String(limit) });
    return this.http.get<PatientLookupResult[]>(this.url(`/patients/search?${params.toString()}`));
  }

  lookupByMobile(mobile: string): Observable<PatientMobileLookup> {
    const params = new URLSearchParams({ mobile });
    return this.http.get<PatientMobileLookup>(this.url(`/patients/by-mobile?${params.toString()}`));
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
