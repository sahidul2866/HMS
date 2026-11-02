import { DestroyRef, Injectable, inject, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ConnectionStateService {
  readonly offline = signal(!navigator.onLine);
  readonly cachedAt = signal<number | null>(null);
  readonly lightMode = signal(false);
  readonly sessionExpired = signal(false);

  constructor() {
    const offline = () => this.offline.set(true);
    const online = () => this.offline.set(false);
    window.addEventListener('offline', offline);
    window.addEventListener('online', online);
    inject(DestroyRef).onDestroy(() => {
      window.removeEventListener('offline', offline);
      window.removeEventListener('online', online);
    });
  }
}
