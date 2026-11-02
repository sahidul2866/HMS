import { HttpInterceptorFn, HttpResponse, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, of, tap, throwError } from 'rxjs';
import { SessionService } from '../services/session.service';
import { ConnectionStateService } from '../services/connection-state.service';
import { runtimeConfig } from '../config/runtime-config';

/** Tab-local only: patient records are never persisted to browser storage. */
@Injectable({ providedIn: 'root' })
export class OfflineResponseCache {
  readonly entries = new Map<string, { response: HttpResponse<unknown>; at: number }>();
  readonly stale = new Map<string, number>();
  generation = 0;
  clear(): void {
    this.generation += 1;
    this.entries.clear();
    this.stale.clear();
  }
  constructor() {
    const state = inject(ConnectionStateService);
    inject(SessionService).state$.subscribe(() => {
      this.clear();
      state.cachedAt.set(null);
    });
  }
}

export const offlineInterceptor: HttpInterceptorFn = (request, next) => {
  const session = inject(SessionService);
  const state = inject(ConnectionStateService);
  const cache = inject(OfflineResponseCache);
  if (request.url.includes('/queue/speech') || !request.url.startsWith(`${runtimeConfig.apiBaseUrl}/`) || /\/(auth|patient-auth)\//.test(request.url)) {
    return next(request);
  }
  const cacheable = !/\/(queue|outpatient)\/|\/appointments\/doctor-slots/.test(request.url) && request.method === 'GET' && request.responseType === 'json' && session.snapshot.authenticated;
  const generation = cache.generation;
  const key = `${session.snapshot.user?.principal_type}:${session.snapshot.user?.id}:${request.urlWithParams}`;
  const cached = cacheable ? cache.entries.get(key) : undefined;
  const fallback = () => {
    if (cached && generation === cache.generation) {
      cache.stale.set(key, cached.at);
      state.cachedAt.set(Math.min(...cache.stale.values()));
      return of(cached.response.clone({ body: structuredClone(cached.response.body) }));
    }
    return throwError(() => new HttpErrorResponse({ status: 0, statusText: 'Offline', url: request.url }));
  };
  if (state.offline() || (state.lightMode() && cached)) return fallback();
  return next(request).pipe(
    tap((event) => {
      if (!(event instanceof HttpResponse)) return;
      if (cacheable && generation === cache.generation) {
        if (cache.entries.size >= 100) cache.entries.delete(cache.entries.keys().next().value!);
        cache.entries.set(key, { response: event.clone({ body: structuredClone(event.body) }), at: Date.now() });
        cache.stale.delete(key);
        state.cachedAt.set(cache.stale.size ? Math.min(...cache.stale.values()) : null);
      } else if (request.method !== 'GET') {
        cache.clear();
      }
    }),
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 0 && cached) return fallback();
      return throwError(() => error);
    })
  );
};
