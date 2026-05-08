import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
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
  private readonly dataSync = inject(DataSyncService);

  getSummary(): Observable<RadiologySummary> {
    return this.cache.get('radiology:summary', () => this.http.get<RadiologySummary>(this.url('/radiology/summary')));
  }

  listWorklist(): Observable<InvestigationWorkItem[]> {
    return this.cache.get('radiology:worklist', () => this.http.get<InvestigationWorkItem[]>(this.url('/radiology/worklist')));
  }

  updateResult(orderId: string, payload: InvestigationResultPayload): Observable<InvestigationWorkItem> {
    return this.http.put<InvestigationWorkItem>(this.url(`/radiology/worklist/${orderId}`), payload).pipe(
      tap((workItem) => {
        this.clearRadiologyCaches();
        this.publishRadiologyEvent(workItem, workItem.status === 'verified' ? 'radiology.report.uploaded' : 'lab.order.created', workItem.status === 'verified' ? 'Radiology report available.' : 'Radiology order status updated.');
      })
    );
  }

  getViewer(orderId: string): Observable<RadiologyViewerPayload> {
    return this.http.get<RadiologyViewerPayload>(this.url(`/radiology/orders/${orderId}/viewer`));
  }

  linkPacsStudy(payload: PACSLinkPayload): Observable<{ order_id: string }> {
    return this.http.post<{ order_id: string }>(this.url('/radiology/pacs/link'), payload).pipe(
      tap((response) => {
        this.clearRadiologyCaches();
        this.publishRadiologyOrderEvent(response.order_id, 'radiology.report.uploaded', 'Radiology PACS study linked.');
      })
    );
  }

  uploadDicom(orderId: string, file: File): Observable<{ order_id: string }> {
    const form = new FormData();
    form.append('dicom_file', file);
    return this.http.post<{ order_id: string }>(this.url(`/radiology/orders/${orderId}/upload-dicom`), form).pipe(
      tap((response) => {
        this.clearRadiologyCaches();
        this.publishRadiologyOrderEvent(response.order_id, 'radiology.report.uploaded', 'Radiology image uploaded.');
      })
    );
  }

  addReport(payload: RadiologyReportPayload): Observable<unknown> {
    return this.http.post(this.url('/radiology/report'), payload).pipe(
      tap(() => {
        this.clearRadiologyCaches();
        this.publishRadiologyOrderEvent(payload.order_id, 'radiology.report.uploaded', 'Radiology report available.');
      })
    );
  }

  markCompleted(orderId: string): Observable<unknown> {
    return this.http.post(this.url(`/radiology/orders/${orderId}/complete`), {}).pipe(
      tap(() => {
        this.clearRadiologyCaches();
        this.publishRadiologyOrderEvent(orderId, 'radiology.report.uploaded', 'Radiology order completed.');
      })
    );
  }

  listSimulatorMachines(): Observable<RadiologySimulatorMachine[]> {
    return this.cache.get('radiology:simulator:machines', () => this.http.get<RadiologySimulatorMachine[]>(this.url('/radiology/simulator/machines')));
  }

  simulateMachineFeed(orderId: string, payload: RadiologySimulatorFeedPayload): Observable<RadiologySimulatorFeedResponse> {
    return this.http
      .post<RadiologySimulatorFeedResponse>(this.url(`/radiology/orders/${orderId}/simulate-machine`), payload)
      .pipe(
        tap((response) => {
          this.clearRadiologyCaches();
          this.publishRadiologyOrderEvent(response.order_id, 'radiology.report.uploaded', 'Radiology machine result updated.');
        })
      );
  }

  private clearRadiologyCaches(): void {
    this.cache.clearPrefix('radiology:');
    this.cache.clearPrefix('diagnostics:');
    this.cache.clearPrefix('opd:');
  }

  private publishRadiologyEvent(workItem: InvestigationWorkItem, name: 'radiology.report.uploaded' | 'lab.order.created', message: string): void {
    this.dataSync.publish({
      name,
      entityType: 'radiology_order',
      entityId: workItem.order_id,
      patientId: workItem.patient_id,
      visitId: workItem.visit_id,
      modules: ['radiology', 'opd', 'patients', 'billing', 'dashboard'],
      cachePrefixes: ['radiology:', 'diagnostics:', 'opd:', 'patients:', 'billing:', 'dashboard:'],
      message,
    });
  }

  private publishRadiologyOrderEvent(orderId: string, name: 'radiology.report.uploaded' | 'lab.order.created', message: string): void {
    this.dataSync.publish({
      name,
      entityType: 'radiology_order',
      entityId: orderId,
      modules: ['radiology', 'opd', 'patients', 'billing', 'dashboard'],
      cachePrefixes: ['radiology:', 'diagnostics:', 'opd:', 'patients:', 'billing:', 'dashboard:'],
      message,
    });
  }
}
