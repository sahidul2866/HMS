import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  InvestigationResultPayload,
  InvestigationWorkItem,
  PACSLinkPayload,
  RadiologyReportPayload,
  RadiologySimulatorFeedPayload,
  RadiologySimulatorFeedResponse,
  RadiologySimulatorMachine,
  RadiologySummary,
  RadiologyViewerPayload,
} from '../models/radiology.models';

@Injectable({ providedIn: 'root' })
export class RadiologyServiceApi extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getSummary(): Observable<RadiologySummary> {
    return this.cache.get('radiology:summary', () => this.http.get<RadiologySummary>(this.url('/radiology/summary')));
  }

  listWorklist(): Observable<InvestigationWorkItem[]> {
    return this.cache.get('radiology:worklist', () => this.http.get<InvestigationWorkItem[]>(this.url('/radiology/worklist')));
  }

  updateResult(orderId: string, payload: InvestigationResultPayload): Observable<InvestigationWorkItem> {
    return this.http.put<InvestigationWorkItem>(this.url(`/radiology/worklist/${orderId}`), payload).pipe(tap(() => this.cache.clearPrefix('radiology:')));
  }

  getViewer(orderId: string): Observable<RadiologyViewerPayload> {
    return this.http.get<RadiologyViewerPayload>(this.url(`/radiology/orders/${orderId}/viewer`));
  }

  linkPacsStudy(payload: PACSLinkPayload): Observable<{ order_id: string }> {
    return this.http.post<{ order_id: string }>(this.url('/radiology/pacs/link'), payload).pipe(tap(() => this.cache.clearPrefix('radiology:')));
  }

  uploadDicom(orderId: string, file: File): Observable<{ order_id: string }> {
    const form = new FormData();
    form.append('dicom_file', file);
    return this.http.post<{ order_id: string }>(this.url(`/radiology/orders/${orderId}/upload-dicom`), form).pipe(tap(() => this.cache.clearPrefix('radiology:')));
  }

  addReport(payload: RadiologyReportPayload): Observable<unknown> {
    return this.http.post(this.url('/radiology/report'), payload).pipe(tap(() => this.cache.clearPrefix('radiology:')));
  }

  markCompleted(orderId: string): Observable<unknown> {
    return this.http.post(this.url(`/radiology/orders/${orderId}/complete`), {}).pipe(tap(() => this.cache.clearPrefix('radiology:')));
  }

  listSimulatorMachines(): Observable<RadiologySimulatorMachine[]> {
    return this.cache.get('radiology:simulator:machines', () => this.http.get<RadiologySimulatorMachine[]>(this.url('/radiology/simulator/machines')));
  }

  simulateMachineFeed(orderId: string, payload: RadiologySimulatorFeedPayload): Observable<RadiologySimulatorFeedResponse> {
    return this.http
      .post<RadiologySimulatorFeedResponse>(this.url(`/radiology/orders/${orderId}/simulate-machine`), payload)
      .pipe(tap(() => this.cache.clearPrefix('radiology:')));
  }
}
