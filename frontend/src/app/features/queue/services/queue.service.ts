import { HttpContext } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { SKIP_GLOBAL_LOADER } from '../../../core/http/http-context.tokens';
import { QueueCounter, QueueDisplay, QueueSetting, QueueSummary, QueueToken } from '../models/queue.models';

@Injectable({ providedIn: 'root' })
export class QueueService extends ApiBaseService {
  listTokens(params: Record<string, string | number | boolean | null | undefined> = {}): Observable<QueueToken[]> {
    const clean: Record<string, string | number | boolean> = {};
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') clean[key] = value;
    });
    return this.http.get<QueueToken[]>(this.url('/queue/tokens'), { params: clean as any, context: new HttpContext().set(SKIP_GLOBAL_LOADER, true) });
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

  updatePriority(id: string, priority: string, reason: string): Observable<QueueToken> {
    return this.http.patch<QueueToken>(this.url(`/queue/tokens/${id}/priority`), { priority, reason });
  }

  listCounters(module?: string): Observable<QueueCounter[]> {
    return this.http.get<QueueCounter[]>(this.url('/queue/counters'), { params: module ? { module } : {} });
  }

  createCounter(payload: Partial<QueueCounter>): Observable<QueueCounter> {
    return this.http.post<QueueCounter>(this.url('/queue/counters'), payload);
  }

  summary(params: { queue_scope?: string | null; doctor_user_id?: string | null } = {}): Observable<QueueSummary> {
    const clean = Object.fromEntries(Object.entries(params).filter(([, value]) => !!value)) as Record<string, string>;
    return this.http.get<QueueSummary>(this.url('/queue/summary'), { params: clean, context: new HttpContext().set(SKIP_GLOBAL_LOADER, true) });
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

  updateCounterStatus(counterId: string, status: 'active' | 'paused' | 'closed'): Observable<QueueCounter> {
    return this.http.patch<QueueCounter>(this.url(`/queue/counters/${counterId}/status`), { status });
  }
}
