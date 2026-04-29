import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { ClinicalOperationsSummary, ReportCatalog } from '../models/reporting.models';

@Injectable({ providedIn: 'root' })
export class ReportingServiceApi extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getClinicalSummary(): Observable<ClinicalOperationsSummary> {
    return this.cache.get('reporting:clinical-summary', () => this.http.get<ClinicalOperationsSummary>(this.url('/reporting/clinical-summary')));
  }

  getCatalog(): Observable<ReportCatalog> {
    return this.cache.get('reporting:catalog', () => this.http.get<ReportCatalog>(this.url('/reporting/catalog')));
  }
}
