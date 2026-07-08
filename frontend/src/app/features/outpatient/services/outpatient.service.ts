import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import { OutpatientDashboard, OutpatientReport, UnifiedOutpatientQueueItem } from '../models/outpatient.models';

@Injectable({ providedIn: 'root' })
export class OutpatientService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  dashboard(params: Record<string, string | null | undefined> = {}): Observable<OutpatientDashboard> {
    const query = this.query(params);
    return this.cache.get(`outpatient:dashboard:${query}`, () => this.http.get<OutpatientDashboard>(this.url(`/outpatient/dashboard${query}`)));
  }

  queue(params: Record<string, string | null | undefined> = {}): Observable<UnifiedOutpatientQueueItem[]> {
    const query = this.query(params);
    return this.cache.get(`outpatient:queue:${query}`, () => this.http.get<UnifiedOutpatientQueueItem[]>(this.url(`/outpatient/queue${query}`)));
  }

  action(tokenId: string, action: string, notes?: string): Observable<UnifiedOutpatientQueueItem> {
    return this.http.post<UnifiedOutpatientQueueItem>(this.url(`/outpatient/queue/${tokenId}/action`), { action, notes }).pipe(tap(() => this.publish()));
  }

  report(params: Record<string, string | null | undefined>): Observable<OutpatientReport> {
    const query = this.query(params);
    return this.http.get<OutpatientReport>(this.url(`/outpatient/reports${query}`));
  }

  clearCache(): void {
    this.cache.clearPrefix('outpatient:');
  }

  private publish(): void {
    this.clearCache();
    this.dataSync.publish({
      name: 'data.updated',
      entityType: 'outpatient',
      modules: ['outpatient', 'opd', 'telemedicine', 'queue', 'patients', 'billing', 'pharmacy', 'laboratory', 'radiology', 'notifications', 'dashboard'],
      cachePrefixes: ['outpatient:', 'opd:', 'telemedicine:', 'queue:', 'patients:', 'billing:', 'pharmacy:', 'laboratory:', 'radiology:', 'notifications:', 'dashboard:'],
      message: 'Outpatient queue updates are available.',
    });
  }

  private query(params: Record<string, string | number | boolean | null | undefined>): string {
    const urlParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') urlParams.set(key, String(value));
    }
    const query = urlParams.toString();
    return query ? `?${query}` : '';
  }
}
