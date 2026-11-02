import { Injectable } from '@angular/core';
import { Observable, of, shareReplay, tap } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiCacheService {
  private readonly persistentPrefix = 'hms-api-cache:';
  /** Stored lookups are reused for this long; after that the next read asks the server again. */
  private readonly persistentTtlMs = 2 * 60 * 1000;
  private readonly cache = new Map<string, Observable<unknown>>();
  private readonly fetchedAt = new Map<string, number>();

  get<T>(key: string, factory: () => Observable<T>): Observable<T> {
    if (!this.cache.has(key)) {
      this.cache.set(key, factory().pipe(shareReplay(1)));
    }
    return this.cache.get(key)! as Observable<T>;
  }

  getPersistent<T>(key: string, factory: () => Observable<T>): Observable<T> {
    const stored = this.readStored<T>(key);
    if (stored !== null) {
      return of(stored);
    }
    const fetchedAt = this.fetchedAt.get(key);
    if (!this.cache.has(key) || fetchedAt === undefined || Date.now() - fetchedAt > this.persistentTtlMs) {
      this.fetchedAt.set(key, Date.now());
      this.cache.set(
        key,
        factory().pipe(
          tap((value) => this.writeStored(key, value)),
          shareReplay(1)
        )
      );
    }
    return this.cache.get(key)! as Observable<T>;
  }

  clear(key: string): void {
    this.cache.delete(key);
    sessionStorage.removeItem(this.storageKey(key));
  }

  clearPrefix(prefix: string): void {
    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) {
        this.cache.delete(key);
      }
    }
    for (const key of this.sessionKeys()) {
      if (key.startsWith(this.storageKey(prefix))) {
        sessionStorage.removeItem(key);
      }
    }
  }

  clearAll(): void {
    this.cache.clear();
    for (const key of this.sessionKeys()) {
      if (key.startsWith(this.persistentPrefix)) {
        sessionStorage.removeItem(key);
      }
    }
  }

  private storageKey(key: string): string {
    return `${this.persistentPrefix}${key}`;
  }

  private readStored<T>(key: string): T | null {
    const raw = sessionStorage.getItem(this.storageKey(key));
    if (!raw) {
      return null;
    }
    try {
      const entry = JSON.parse(raw) as { storedAt?: number; value?: T };
      if (typeof entry?.storedAt !== 'number' || Date.now() - entry.storedAt > this.persistentTtlMs) {
        sessionStorage.removeItem(this.storageKey(key));
        return null;
      }
      return (entry.value ?? null) as T | null;
    } catch {
      sessionStorage.removeItem(this.storageKey(key));
      return null;
    }
  }

  private writeStored<T>(key: string, value: T): void {
    // An empty list usually means the setup has not been done yet; keeping it would hide what others add next.
    if (Array.isArray(value) && !value.length) {
      return;
    }
    try {
      sessionStorage.setItem(this.storageKey(key), JSON.stringify({ storedAt: Date.now(), value }));
    } catch {
      // Storage can be unavailable or full; in-memory cache still covers the active tab.
    }
  }

  private sessionKeys(): string[] {
    return Array.from({ length: sessionStorage.length }, (_, index) => sessionStorage.key(index)).filter((key): key is string => !!key);
  }
}
