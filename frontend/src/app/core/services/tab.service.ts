import { Injectable, inject, signal } from '@angular/core';
import { ActivatedRouteSnapshot, NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { TabRouteReuseStrategy } from './tab-route-reuse.strategy';

export interface AppTab {
  path: string;
  label: string;
}

@Injectable({ providedIn: 'root' })
export class TabService {
  private static readonly STORAGE_KEY = 'hms.tabs';

  private readonly router = inject(Router);
  private readonly routeReuseStrategy = inject(TabRouteReuseStrategy);
  private readonly tabsSignal = signal<AppTab[]>([]);
  private readonly activePathSignal = signal('');

  readonly tabs = this.tabsSignal.asReadonly();
  readonly activePath = this.activePathSignal.asReadonly();

  constructor() {
    this.restoreState();

    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)).subscribe((event) => {
      this.syncRoute(event.urlAfterRedirects);
    });
  }

  activate(path: string): void {
    void this.router.navigateByUrl(path);
  }

  close(path: string): void {
    const currentTabs = this.tabsSignal();
    const index = currentTabs.findIndex((tab) => tab.path === path);
    if (index === -1) {
      return;
    }

    const remainingTabs = currentTabs.filter((tab) => tab.path !== path);
    this.tabsSignal.set(remainingTabs);
    this.routeReuseStrategy.evict(path);
    this.persistState();

    if (this.activePathSignal() !== path) {
      return;
    }

    const fallback = remainingTabs[index] ?? remainingTabs[index - 1] ?? remainingTabs[remainingTabs.length - 1];
    if (fallback) {
      this.activate(fallback.path);
      return;
    }

    this.activePathSignal.set('');
    this.persistState();
    void this.router.navigateByUrl('/dashboard');
  }

  clear(): void {
    this.tabsSignal.set([]);
    this.activePathSignal.set('');
    this.routeReuseStrategy.clear();
    sessionStorage.removeItem(TabService.STORAGE_KEY);
  }

  private syncRoute(rawUrl: string): void {
    const path = this.normalizePath(rawUrl);
    if (!path || path.startsWith('/auth')) {
      return;
    }

    const label = this.resolveLabel();
    const currentTabs = this.tabsSignal();
    const existing = currentTabs.find((tab) => tab.path === path);
    if (existing) {
      this.activePathSignal.set(path);
      this.persistState();
      return;
    }

    this.tabsSignal.set([...currentTabs, { path, label }]);
    this.activePathSignal.set(path);
    this.persistState();
  }

  private resolveLabel(): string {
    let snapshot: ActivatedRouteSnapshot | null = this.router.routerState.snapshot.root;
    let label = 'Workspace';

    while (snapshot?.firstChild) {
      snapshot = snapshot.firstChild;
      label = (snapshot.data['tabLabel'] as string | undefined) ?? label;
    }

    return label;
  }

  private normalizePath(rawUrl: string): string {
    const [path] = rawUrl.split('?');
    return path;
  }

  private persistState(): void {
    sessionStorage.setItem(
      TabService.STORAGE_KEY,
      JSON.stringify({
        tabs: this.tabsSignal(),
        activePath: this.activePathSignal(),
      })
    );
  }

  private restoreState(): void {
    const rawState = sessionStorage.getItem(TabService.STORAGE_KEY);
    if (!rawState) {
      return;
    }

    try {
      const parsed = JSON.parse(rawState) as { tabs?: AppTab[]; activePath?: string };
      this.tabsSignal.set(Array.isArray(parsed.tabs) ? parsed.tabs : []);
      this.activePathSignal.set(parsed.activePath ?? '');
    } catch {
      sessionStorage.removeItem(TabService.STORAGE_KEY);
    }
  }
}
