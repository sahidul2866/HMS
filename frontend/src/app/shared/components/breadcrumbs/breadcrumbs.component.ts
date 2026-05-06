import { CommonModule, Location } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';

import { MenuItem, menuConfig } from '../../../navigation/menu.config';

type Breadcrumb = {
  label: string;
  url: string;
};

@Component({
  selector: 'app-breadcrumbs',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    @if (breadcrumbs().length > 1) {
      <nav class="breadcrumbs" aria-label="Breadcrumb">
        <button class="crumb-back" type="button" (click)="goBack()">← Back</button>
        @for (crumb of breadcrumbs(); track crumb.url; let last = $last) {
          @if (!last) {
            <a class="crumb" [routerLink]="crumb.url">{{ crumb.label }}</a>
            <span class="crumb-sep" aria-hidden="true">/</span>
          } @else {
            <span class="crumb current" aria-current="page">{{ crumb.label }}</span>
          }
        }
      </nav>
    }
  `,
})
export class BreadcrumbsComponent {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly location = inject(Location);

  private readonly crumbs = signal<Breadcrumb[]>([]);
  readonly breadcrumbs = computed(() => this.crumbs());

  constructor() {
    this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe(() => {
      this.crumbs.set(this.buildCrumbs());
    });
    this.crumbs.set(this.buildCrumbs());
  }

  goBack(): void {
    this.location.back();
  }

  private buildCrumbs(): Breadcrumb[] {
    const crumbs: Breadcrumb[] = [{ label: 'Home', url: '/dashboard' }];
    let current = this.route.root;
    let url = '';
    const currentPath = this.normalizePath(this.router.url);
    const menuTrail = this.findMenuTrail(menuConfig, currentPath);

    for (const crumb of menuTrail) {
      this.pushCrumb(crumbs, crumb);
    }

    while (current.firstChild) {
      current = current.firstChild;
      const segment = current.snapshot.url.map((s) => s.path).filter(Boolean).join('/');
      if (segment) {
        url += `/${segment}`;
      }

      const label = (current.snapshot.data?.['tabLabel'] as string | undefined)?.trim();
      if (label) {
        this.pushCrumb(crumbs, { label, url: url || '/' });
      }
    }

    return crumbs;
  }

  private findMenuTrail(items: MenuItem[], currentPath: string): Breadcrumb[] {
    const orderedItems = [...items].sort((left, right) => (right.route?.length ?? 0) - (left.route?.length ?? 0));

    for (const item of orderedItems) {
      if (item.children?.length) {
        const childTrail = this.findMenuTrail(item.children, currentPath);
        if (childTrail.length) {
          return [{ label: item.label, url: item.route || childTrail[0].url }, ...childTrail];
        }
      }

      if (item.route && this.routeMatches(item.route, currentPath)) {
        return [{ label: item.label, url: item.route }];
      }
    }

    return [];
  }

  private routeMatches(route: string, currentPath: string): boolean {
    return currentPath === route || currentPath.startsWith(`${route}/`);
  }

  private normalizePath(rawUrl: string): string {
    return rawUrl.split('?')[0].split('#')[0] || '/';
  }

  private pushCrumb(crumbs: Breadcrumb[], crumb: Breadcrumb): void {
    const last = crumbs[crumbs.length - 1];
    if (last?.label === crumb.label || last?.url === crumb.url) {
      return;
    }
    crumbs.push(crumb);
  }
}
