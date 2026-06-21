import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, DetachedRouteHandle, RouteReuseStrategy } from '@angular/router';

@Injectable()
export class TabRouteReuseStrategy implements RouteReuseStrategy {
  private readonly storedHandles = new Map<string, DetachedRouteHandle>();
  private readonly invalidatedPaths = new Set<string>();

  shouldDetach(route: ActivatedRouteSnapshot): boolean {
    const key = this.buildKey(route);
    return this.isReusableRoute(route) && !this.invalidatedPaths.has(key);
  }

  store(route: ActivatedRouteSnapshot, handle: DetachedRouteHandle | null): void {
    const key = this.buildKey(route);
    if (!key) {
      return;
    }

    if (!handle) {
      this.storedHandles.delete(key);
      return;
    }

    this.storedHandles.set(key, handle);
  }

  shouldAttach(route: ActivatedRouteSnapshot): boolean {
    const key = this.buildKey(route);
    if (key && this.invalidatedPaths.has(key)) {
      this.storedHandles.delete(key);
      this.invalidatedPaths.delete(key);
      return false;
    }
    return !!key && this.storedHandles.has(key);
  }

  retrieve(route: ActivatedRouteSnapshot): DetachedRouteHandle | null {
    const key = this.buildKey(route);
    return key ? this.storedHandles.get(key) ?? null : null;
  }

  shouldReuseRoute(future: ActivatedRouteSnapshot, curr: ActivatedRouteSnapshot): boolean {
    const futureKey = this.buildKey(future);
    const currentKey = this.buildKey(curr);
    return future.routeConfig === curr.routeConfig
      && futureKey === currentKey
      && !this.invalidatedPaths.has(futureKey);
  }

  evict(path: string): void {
    const normalized = this.normalizePath(path);
    for (const key of this.storedHandles.keys()) {
      if (key === normalized) {
        this.storedHandles.delete(key);
      }
    }
  }

  clear(): void {
    this.storedHandles.clear();
    this.invalidatedPaths.clear();
  }

  invalidateModules(modules: string[]): void {
    for (const key of [...this.storedHandles.keys()]) {
      if (this.matchesAnyModule(key, modules)) {
        this.storedHandles.delete(key);
      }
    }
  }

  invalidatePath(path: string): void {
    const normalized = this.normalizePath(path);
    this.storedHandles.delete(normalized);
    this.invalidatedPaths.add(normalized);
  }

  matchesAnyModule(path: string, modules: string[]): boolean {
    const root = this.normalizePath(path).split('/').filter(Boolean)[0] ?? '';
    return modules.some((module) => this.moduleRoots(module).includes(root));
  }

  private isReusableRoute(route: ActivatedRouteSnapshot): boolean {
    const key = this.buildKey(route);
    if (!key) {
      return false;
    }

    return !key.startsWith('/auth');
  }

  private buildKey(route: ActivatedRouteSnapshot): string {
    const segments = route.pathFromRoot
      .flatMap((snapshot) => snapshot.url.map((segment) => segment.path))
      .filter(Boolean);

    if (!segments.length) {
      return route.routeConfig?.path === '' ? '/dashboard' : '';
    }

    return this.normalizePath(`/${segments.join('/')}`);
  }

  private normalizePath(path: string): string {
    return path.split('?')[0].split('#')[0];
  }

  private moduleRoots(module: string): string[] {
    const aliases: Record<string, string[]> = {
      admin: ['admin'],
      appointments: ['appointments'],
      billing: ['billing'],
      dashboard: ['dashboard'],
      emergency: ['er'],
      er: ['er'],
      ipd: ['ipd'],
      laboratory: ['laboratory', 'diagnostics'],
      notifications: ['notifications'],
      opd: ['opd'],
      patients: ['patients'],
      pharmacy: ['pharmacy'],
      radiology: ['radiology', 'diagnostics'],
    };
    return aliases[module] ?? [module];
  }
}
