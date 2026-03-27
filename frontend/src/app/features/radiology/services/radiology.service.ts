import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { InvestigationResultPayload, InvestigationWorkItem, RadiologySummary } from '../models/radiology.models';

@Injectable({ providedIn: 'root' })
export class RadiologyServiceApi extends ApiBaseService {
  getSummary(): Observable<RadiologySummary> {
    return this.http.get<RadiologySummary>(this.url('/radiology/summary'));
  }

  listWorklist(): Observable<InvestigationWorkItem[]> {
    return this.http.get<InvestigationWorkItem[]>(this.url('/radiology/worklist'));
  }

  updateResult(orderId: string, payload: InvestigationResultPayload): Observable<InvestigationWorkItem> {
    return this.http.put<InvestigationWorkItem>(this.url(`/radiology/worklist/${orderId}`), payload);
  }
}
