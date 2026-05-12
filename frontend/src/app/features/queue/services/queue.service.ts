import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { QueueCounter, QueueDisplay, QueueSetting, QueueSummary, QueueToken } from '../models/queue.models';

@Injectable({ providedIn: 'root' })
export class QueueService extends ApiBaseService {
  listTokens(params: Record<string, string | number | boolean | null | undefined> = {}): Observable<QueueToken[]> {
    const clean: Record<string, string | number | boolean> = {};
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') clean[key] = value;
    });
    return this.http.get<QueueToken[]>(this.url('/queue/tokens'), { params: clean as any });
  }

  callNext(payload: { queue_scope: string; counter_id?: string | null; doctor_user_id?: string | null }): Observable<QueueToken> {
    const params: Record<string, string> = { queue_scope: payload.queue_scope };
    if (payload.counter_id) params['counter_id'] = payload.counter_id;
    if (payload.doctor_user_id) params['doctor_user_id'] = payload.doctor_user_id;
    return this.http.post<QueueToken>(this.url('/queue/call-next'), null, { params });
  }

  updateStatus(id: string, status: string, counter_id?: string | null, notes?: string | null): Observable<QueueToken> {
    return this.http.post<QueueToken>(this.url(`/queue/tokens/${id}/status`), { status, counter_id: counter_id || null, notes: notes || null });
  }

  transfer(id: string, payload: Record<string, unknown>): Observable<QueueToken> {
    return this.http.post<QueueToken>(this.url(`/queue/tokens/${id}/transfer`), payload);
  }

  listCounters(module?: string): Observable<QueueCounter[]> {
    return this.http.get<QueueCounter[]>(this.url('/queue/counters'), { params: module ? { module } : {} });
  }

  createCounter(payload: Partial<QueueCounter>): Observable<QueueCounter> {
    return this.http.post<QueueCounter>(this.url('/queue/counters'), payload);
  }

  summary(): Observable<QueueSummary> {
    return this.http.get<QueueSummary>(this.url('/queue/summary'));
  }

  display(scope: string): Observable<QueueDisplay> {
    return this.http.get<QueueDisplay>(this.url(`/queue/display/${scope}`));
  }

  listSettings(): Observable<QueueSetting[]> {
    return this.http.get<QueueSetting[]>(this.url('/queue/settings'));
  }

  saveSetting(payload: { setting_key: string; setting_value: Record<string, unknown> }): Observable<QueueSetting> {
    return this.http.post<QueueSetting>(this.url('/queue/settings'), payload);
  }
}
