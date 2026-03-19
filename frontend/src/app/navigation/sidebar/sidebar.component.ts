import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs';

import { SessionService } from '../../core/services/session.service';
import { MenuItem, menuConfig } from '../menu.config';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  @Input() collapsed = false;
  @Output() collapsedChange = new EventEmitter<boolean>();

  items: MenuItem[] = [];
  expandedGroups = new Set<string>();

  constructor() {
    this.sessionService.state$.subscribe(() => {
      this.items = this.filterItems(menuConfig);
      this.expandActiveGroups();
    });
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)).subscribe(() => {
      this.expandActiveGroups();
    });
  }

  toggleSidebar(): void {
    this.collapsedChange.emit(!this.collapsed);
  }

  toggleGroup(label: string): void {
    if (this.expandedGroups.has(label)) {
      this.expandedGroups.delete(label);
      return;
    }
    this.expandedGroups.add(label);
  }

  isExpanded(label: string): boolean {
    return this.expandedGroups.has(label);
  }

  isGroupActive(item: MenuItem): boolean {
    return item.children?.some((child) => this.isRouteActive(child.route)) ?? false;
  }

  isRouteActive(route?: string): boolean {
    return !!route && this.router.url.startsWith(route);
  }

  private filterItems(items: MenuItem[]): MenuItem[] {
    return items
      .map((item) => {
        const filteredChildren = item.children ? this.filterItems(item.children) : undefined;
        return {
          ...item,
          children: filteredChildren,
        };
      })
      .filter((item) => {
        if (item.children?.length) {
          return item.children.length > 0;
        }
        return this.sessionService.hasPermission(item.permissions);
      });
  }

  private expandActiveGroups(): void {
    for (const item of this.items) {
      if (item.children?.length && this.isGroupActive(item)) {
        this.expandedGroups.add(item.label);
      }
    }
  }
}
