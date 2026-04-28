import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { InvestigationResultPayload, InvestigationWorkItem, LaboratorySummary } from '../models/laboratory.models';

@Injectable({ providedIn: 'root' })
export class LaboratoryServiceApi extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getSummary(): Observable<LaboratorySummary> {
    return this.cache.get('laboratory:summary', () => this.http.get<LaboratorySummary>(this.url('/laboratory/summary')));
  }

  listWorklist(): Observable<InvestigationWorkItem[]> {
    return this.cache.get('laboratory:worklist', () => this.http.get<InvestigationWorkItem[]>(this.url('/laboratory/worklist')));
  }

  updateResult(orderId: string, payload: InvestigationResultPayload): Observable<InvestigationWorkItem> {
    return this.http.put<InvestigationWorkItem>(this.url(`/laboratory/worklist/${orderId}`), payload).pipe(tap(() => this.cache.clearPrefix('laboratory:')));
  }
}
