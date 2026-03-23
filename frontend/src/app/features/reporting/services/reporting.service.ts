import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ClinicalOperationsSummary } from '../models/reporting.models';

@Injectable({ providedIn: 'root' })
export class ReportingServiceApi extends ApiBaseService {
  getClinicalSummary(): Observable<ClinicalOperationsSummary> {
    return this.http.get<ClinicalOperationsSummary>(this.url('/reporting/clinical-summary'));
  }
}
