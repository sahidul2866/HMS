import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import {
  CreateERVisitPayload,
  ERSummary,
  ERVisit,
  ERVisitAmbulance,
  ERVisitAmbulancePayload,
  ERVisitAssignmentPayload,
  ERVisitStatusPayload,
  ERVisitTriagePayload,
  ERVisitTreatmentPayload,
  ERConvertToIPDPayload,
} from '../models/er.models';

@Injectable({ providedIn: 'root' })
export class ERService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  listVisits(): Observable<ERVisit[]> {
    return this.cache.get('er:visits', () => this.http.get<ERVisit[]>(this.url('/er/visits')));
  }

  getVisit(visitId: string): Observable<ERVisit> {
    return this.cache.get(`er:visit:${visitId}`, () => this.http.get<ERVisit>(this.url(`/er/visits/${visitId}`)));
  }

  getSummary(): Observable<ERSummary> {
    return this.cache.get('er:summary', () => this.http.get<ERSummary>(this.url('/er/summary')));
  }

  createVisit(payload: CreateERVisitPayload): Observable<ERVisit> {
    return this.http.post<ERVisit>(this.url('/er/visits'), payload).pipe(tap(() => this.clearCache()));
  }

  triageVisit(visitId: string, payload: ERVisitTriagePayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/triage`), payload).pipe(tap(() => this.clearCache()));
  }

  assignVisit(visitId: string, payload: ERVisitAssignmentPayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/assign`), payload).pipe(tap(() => this.clearCache()));
  }

  updateTreatment(visitId: string, payload: ERVisitTreatmentPayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/treatment`), payload).pipe(tap(() => this.clearCache()));
  }

  updateStatus(visitId: string, payload: ERVisitStatusPayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/status`), payload).pipe(tap(() => this.clearCache()));
  }

  createAmbulanceRecord(visitId: string, payload: ERVisitAmbulancePayload): Observable<ERVisitAmbulance> {
    return this.http.post<ERVisitAmbulance>(this.url(`/er/visits/${visitId}/ambulance`), payload).pipe(tap(() => this.clearCache()));
  }

  convertToIPD(visitId: string, payload: ERConvertToIPDPayload): Observable<ERVisit> {
    return this.http.post<ERVisit>(this.url(`/er/visits/${visitId}/convert-to-ipd`), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('er:');
  }
}
