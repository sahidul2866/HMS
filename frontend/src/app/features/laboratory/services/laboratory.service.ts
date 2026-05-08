import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import { InvestigationResultPayload, InvestigationWorkItem, LaboratorySummary } from '../models/laboratory.models';

@Injectable({ providedIn: 'root' })
export class LaboratoryServiceApi extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  getSummary(): Observable<LaboratorySummary> {
    return this.cache.get('laboratory:summary', () => this.http.get<LaboratorySummary>(this.url('/laboratory/summary')));
  }

  listWorklist(): Observable<InvestigationWorkItem[]> {
    return this.cache.get('laboratory:worklist', () => this.http.get<InvestigationWorkItem[]>(this.url('/laboratory/worklist')));
  }

  updateResult(orderId: string, payload: InvestigationResultPayload): Observable<InvestigationWorkItem> {
    return this.http.put<InvestigationWorkItem>(this.url(`/laboratory/worklist/${orderId}`), payload).pipe(
      tap((workItem) => {
        this.cache.clearPrefix('laboratory:');
        this.cache.clearPrefix('diagnostics:');
        this.cache.clearPrefix('opd:');
        this.dataSync.publish({
          name: workItem.status === 'verified' ? 'lab.result.verified' : 'lab.order.created',
          entityType: 'lab_order',
          entityId: workItem.order_id,
          patientId: workItem.patient_id,
          visitId: workItem.visit_id,
          modules: ['laboratory', 'opd', 'patients', 'billing', 'dashboard'],
          cachePrefixes: ['laboratory:', 'diagnostics:', 'opd:', 'patients:', 'billing:', 'dashboard:'],
          message: workItem.status === 'verified' ? 'New lab result available.' : 'Lab order status updated.',
        });
      })
    );
  }
}
