import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { CreateIPDAdmissionPayload, CreateIPDBedPayload, IPDAdmission, IPDBed, IPDSummary } from '../models/ipd.models';

@Injectable({ providedIn: 'root' })
export class IPDService extends ApiBaseService {
  listAdmissions(): Observable<IPDAdmission[]> {
    return this.http.get<IPDAdmission[]>(this.url('/ipd/admissions'));
  }

  getSummary(): Observable<IPDSummary> {
    return this.http.get<IPDSummary>(this.url('/ipd/summary'));
  }

  createAdmission(payload: CreateIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url('/ipd/admissions'), payload);
  }

  listBeds(): Observable<IPDBed[]> {
    return this.http.get<IPDBed[]>(this.url('/ipd/beds'));
  }

  createBed(payload: CreateIPDBedPayload): Observable<IPDBed> {
    return this.http.post<IPDBed>(this.url('/ipd/beds'), payload);
  }

  discharge(admissionId: string, discharge_note?: string | null): Observable<IPDAdmission> {
    return this.http.put<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}/discharge`), { discharge_note: discharge_note || null });
  }
}
