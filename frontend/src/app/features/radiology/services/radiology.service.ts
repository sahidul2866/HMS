import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { InvestigationResultPayload, InvestigationWorkItem, RadiologySummary } from '../models/radiology.models';

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
}
