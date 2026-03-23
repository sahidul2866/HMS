import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, DetachedRouteHandle, RouteReuseStrategy } from '@angular/router';

@Injectable()
export class TabRouteReuseStrategy implements RouteReuseStrategy {
  private readonly storedHandles = new Map<string, DetachedRouteHandle>();

  shouldDetach(route: ActivatedRouteSnapshot): boolean {
    return this.isReusableRoute(route);
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
    return !!key && this.storedHandles.has(key);
  }

  retrieve(route: ActivatedRouteSnapshot): DetachedRouteHandle | null {
    const key = this.buildKey(route);
    return key ? this.storedHandles.get(key) ?? null : null;
  }

  shouldReuseRoute(future: ActivatedRouteSnapshot, curr: ActivatedRouteSnapshot): boolean {
    return future.routeConfig === curr.routeConfig;
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
    return path.split('?')[0];
  }
}
