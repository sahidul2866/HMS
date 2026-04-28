import { Injectable } from '@angular/core';
import { Observable, of, shareReplay, tap } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiCacheService {
  private readonly persistentPrefix = 'hms-api-cache:';
  private readonly cache = new Map<string, Observable<unknown>>();

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
    if (!this.cache.has(key)) {
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
      return JSON.parse(raw) as T;
    } catch {
      sessionStorage.removeItem(this.storageKey(key));
      return null;
    }
  }

  private writeStored<T>(key: string, value: T): void {
    try {
      sessionStorage.setItem(this.storageKey(key), JSON.stringify(value));
    } catch {
      // Storage can be unavailable or full; in-memory cache still covers the active tab.
    }
  }

  private sessionKeys(): string[] {
    return Array.from({ length: sessionStorage.length }, (_, index) => sessionStorage.key(index)).filter((key): key is string => !!key);
  }
}
