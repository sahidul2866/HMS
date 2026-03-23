import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class UiStateService {
  private static readonly KEY_PREFIX = 'ui-state:';

  save<T>(key: string, value: T): void {
    sessionStorage.setItem(key, JSON.stringify(value));
  }

  load<T>(key: string): T | null {
    const raw = sessionStorage.getItem(key);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as T;
    } catch {
      sessionStorage.removeItem(key);
      return null;
    }
  }

  clear(key: string): void {
    sessionStorage.removeItem(key);
  }

  clearAll(): void {
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(UiStateService.KEY_PREFIX)) {
        sessionStorage.removeItem(key);
      }
    }
  }
}
