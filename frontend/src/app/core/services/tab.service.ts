import { Injectable, inject, signal } from '@angular/core';
import { ActivatedRouteSnapshot, NavigationEnd, NavigationStart, Router } from '@angular/router';
import { filter } from 'rxjs';

import { NotificationService } from './notification.service';

export interface AppTab {
  path: string;
  label: string;
}

@Injectable({ providedIn: 'root' })
export class TabService {
  readonly maxTabs = 8;

  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);
  private readonly tabsSignal = signal<AppTab[]>([]);
  private readonly activePathSignal = signal('');
  private previousPath = '';
  private restoringBlockedNavigation = false;

  readonly tabs = this.tabsSignal.asReadonly();
  readonly activePath = this.activePathSignal.asReadonly();

  constructor() {
    this.router.events.pipe(filter((event): event is NavigationStart => event instanceof NavigationStart)).subscribe(() => {
      this.previousPath = this.activePathSignal();
    });

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

    if (this.activePathSignal() !== path) {
      return;
    }

    const fallback = remainingTabs[index] ?? remainingTabs[index - 1] ?? remainingTabs[remainingTabs.length - 1];
    if (fallback) {
      this.activate(fallback.path);
      return;
    }

    this.activePathSignal.set('');
    void this.router.navigateByUrl('/dashboard');
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
      return;
    }

    if (currentTabs.length >= this.maxTabs) {
      if (!this.restoringBlockedNavigation) {
        this.restoringBlockedNavigation = true;
        this.notificationService.warning(`Maximum ${this.maxTabs} tabs reached. Close a tab before opening a new one.`);
        const fallback = this.previousPath || currentTabs[currentTabs.length - 1]?.path || '/dashboard';
        void this.router.navigateByUrl(fallback, { replaceUrl: true }).finally(() => {
          this.restoringBlockedNavigation = false;
        });
      }
      return;
    }

    this.tabsSignal.set([...currentTabs, { path, label }]);
    this.activePathSignal.set(path);
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
}
