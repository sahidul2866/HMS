import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
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
  private readonly dataSync = inject(DataSyncService);

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
    return this.http.post<ERVisit>(this.url('/er/visits'), payload).pipe(tap((visit) => this.publishEREvent(visit, 'Emergency patient registered.')));
  }

  triageVisit(visitId: string, payload: ERVisitTriagePayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/triage`), payload).pipe(tap((visit) => this.publishEREvent(visit, 'Emergency triage updated.')));
  }

  assignVisit(visitId: string, payload: ERVisitAssignmentPayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/assign`), payload).pipe(tap((visit) => this.publishEREvent(visit, 'Emergency bed/team assignment updated.')));
  }

  updateTreatment(visitId: string, payload: ERVisitTreatmentPayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/treatment`), payload).pipe(tap((visit) => this.publishEREvent(visit, 'Emergency treatment updated.')));
  }

  updateStatus(visitId: string, payload: ERVisitStatusPayload): Observable<ERVisit> {
    return this.http.put<ERVisit>(this.url(`/er/visits/${visitId}/status`), payload).pipe(tap((visit) => this.publishEREvent(visit, 'Emergency status updated.')));
  }

  createAmbulanceRecord(visitId: string, payload: ERVisitAmbulancePayload): Observable<ERVisitAmbulance> {
    return this.http.post<ERVisitAmbulance>(this.url(`/er/visits/${visitId}/ambulance`), payload).pipe(tap(() => {
      this.clearCache();
      this.dataSync.publish({
        name: 'emergency.status.updated',
        entityType: 'er_visit',
        entityId: visitId,
        modules: ['er', 'patients', 'dashboard'],
        cachePrefixes: ['er:', 'patients:', 'dashboard:'],
        message: 'Emergency ambulance handoff updated.',
      });
    }));
  }

  convertToIPD(visitId: string, payload: ERConvertToIPDPayload): Observable<ERVisit> {
    return this.http.post<ERVisit>(this.url(`/er/visits/${visitId}/convert-to-ipd`), payload).pipe(tap((visit) => this.publishEREvent(visit, 'Emergency patient admitted to IPD.')));
  }

  clearCache(): void {
    this.cache.clearPrefix('er:');
  }

  private publishEREvent(visit: ERVisit, message: string): void {
    this.clearCache();
    this.dataSync.publish({
      name: 'emergency.status.updated',
      entityType: 'er_visit',
      entityId: visit.id,
      patientId: visit.patient?.id,
      modules: ['er', 'patients', 'ipd', 'billing', 'laboratory', 'radiology', 'pharmacy', 'dashboard'],
      cachePrefixes: ['er:', 'patients:', 'ipd:', 'billing:', 'laboratory:', 'radiology:', 'pharmacy:', 'dashboard:'],
      message,
    });
  }
}
