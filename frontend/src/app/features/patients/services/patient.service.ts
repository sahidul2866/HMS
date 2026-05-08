import { Injectable, inject } from '@angular/core';
import { Observable, map, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import { CreatePatientPayload, Patient, PatientClinicalHistory, PatientLookupResult, PatientMobileLookup } from '../models/patient.models';

@Injectable({ providedIn: 'root' })
export class PatientService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  list(): Observable<Patient[]> {
    return this.cache.getPersistent('patients:list', () => this.http.get<Patient[]>(this.url('/patients')));
  }

  search(q: string, limit = 10): Observable<PatientLookupResult[]> {
    const normalized = q.trim().toLowerCase();
    if (!normalized) {
      return this.list().pipe(map(() => []));
    }
    return this.list().pipe(
      map((patients) =>
        patients
          .filter((patient) =>
            [
              patient.patient_number,
              `${patient.first_name} ${patient.last_name}`,
              patient.phone,
              patient.email,
            ]
              .filter(Boolean)
              .some((value) => String(value).toLowerCase().includes(normalized))
          )
          .slice(0, limit)
          .map((patient) => ({
            ...patient,
            full_name: `${patient.first_name} ${patient.last_name}`.trim(),
          }))
      )
    );
  }

  searchByAnyField(q: string, limit = 10): Observable<PatientLookupResult[]> {
    return this.search(q, limit);
  }

  lookupByMobile(mobile: string): Observable<PatientMobileLookup> {
    const params = new URLSearchParams({ mobile });
    return this.cache.get(`patients:mobile:${mobile}`, () => this.http.get<PatientMobileLookup>(this.url(`/patients/by-mobile?${params.toString()}`)));
  }

  get(patientId: string): Observable<Patient> {
    return this.cache.get(`patients:detail:${patientId}`, () => this.http.get<Patient>(this.url(`/patients/${patientId}`)));
  }

  getHistory(patientId: string): Observable<PatientClinicalHistory> {
    return this.cache.get(`patients:history:${patientId}`, () => this.http.get<PatientClinicalHistory>(this.url(`/patients/${patientId}/history`)));
  }

  create(payload: CreatePatientPayload): Observable<Patient> {
    return this.http.post<Patient>(this.url('/patients'), payload).pipe(
      tap((patient) => {
        this.clearCache();
        this.dataSync.publish({
          name: 'patient.updated',
          entityType: 'patient',
          entityId: patient.id,
          patientId: patient.id,
          modules: ['patients', 'appointments', 'opd', 'ipd', 'er', 'billing', 'pharmacy', 'laboratory', 'radiology', 'dashboard'],
          cachePrefixes: ['patients:', 'appointments:', 'opd:', 'ipd:', 'er:', 'billing:', 'pharmacy:', 'laboratory:', 'radiology:', 'dashboard:'],
          message: 'Patient information updated.',
        });
      })
    );
  }

  clearCache(): void {
    this.cache.clearPrefix('patients:');
  }
}
