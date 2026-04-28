import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  CreateIPDAdmissionPayload,
  CreateIPDBedPayload,
  DischargeIPDAdmissionPayload,
  IPDAdmission,
  IPDBed,
  IPDSummary,
  TransferIPDAdmissionPayload,
} from '../models/ipd.models';

@Injectable({ providedIn: 'root' })
export class IPDService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  listAdmissions(): Observable<IPDAdmission[]> {
    return this.cache.get('ipd:admissions', () => this.http.get<IPDAdmission[]>(this.url('/ipd/admissions')));
  }

  getAdmission(admissionId: string): Observable<IPDAdmission> {
    return this.cache.get(`ipd:admission:${admissionId}`, () => this.http.get<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}`)));
  }

  getSummary(): Observable<IPDSummary> {
    return this.cache.get('ipd:summary', () => this.http.get<IPDSummary>(this.url('/ipd/summary')));
  }

  createAdmission(payload: CreateIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url('/ipd/admissions'), payload).pipe(tap(() => this.clearCache()));
  }

  listBeds(): Observable<IPDBed[]> {
    return this.cache.get('ipd:beds', () => this.http.get<IPDBed[]>(this.url('/ipd/beds')));
  }

  createBed(payload: CreateIPDBedPayload): Observable<IPDBed> {
    return this.http.post<IPDBed>(this.url('/ipd/beds'), payload).pipe(tap(() => this.clearCache()));
  }

  discharge(admissionId: string, payload: DischargeIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.put<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}/discharge`), payload).pipe(tap(() => this.clearCache()));
  }

  transfer(admissionId: string, payload: TransferIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.put<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}/transfer`), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('ipd:');
  }
}
