import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DashboardAnalytics } from '../models/dashboard-analytics.models';

export interface DashboardFilters {
  date_from?: string;
  date_to?: string;
  department?: string;
  doctor_id?: string;
  patient_type?: string;
  payment_status?: string;
  module_type?: string;
}

@Injectable({ providedIn: 'root' })
export class DashboardAnalyticsService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getAnalytics(filters: DashboardFilters = {}): Observable<DashboardAnalytics> {
    const query = this.query(filters);
    return this.cache.get(`dashboard:analytics:${query}`, () => this.http.get<DashboardAnalytics>(this.url(`/reporting/dashboard-analytics${query}`)));
  }

  private query(filters: DashboardFilters): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
    const query = params.toString();
    return query ? `?${query}` : '';
  }
}
