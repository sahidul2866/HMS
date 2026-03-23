import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { InvestigationResultPayload, InvestigationWorkItem } from '../models/laboratory.models';

@Injectable({ providedIn: 'root' })
export class LaboratoryServiceApi extends ApiBaseService {
  listWorklist(): Observable<InvestigationWorkItem[]> {
    return this.http.get<InvestigationWorkItem[]>(this.url('/laboratory/worklist'));
  }

  updateResult(orderId: string, payload: InvestigationResultPayload): Observable<InvestigationWorkItem> {
    return this.http.put<InvestigationWorkItem>(this.url(`/laboratory/worklist/${orderId}`), payload);
  }
}
