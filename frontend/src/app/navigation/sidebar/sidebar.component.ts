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
  @Input() mobileOpen = false;
  @Input() mobileMode = false;
  @Output() collapsedChange = new EventEmitter<boolean>();
  @Output() mobileOpenChange = new EventEmitter<boolean>();

  items: MenuItem[] = [];
  expandedGroups = new Set<string>();

  constructor() {
    this.sessionService.state$.subscribe(() => {
      this.items = this.filterItems(menuConfig);
      this.expandActiveGroups();
    });
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)).subscribe(() => {
      this.expandActiveGroups();
      if (this.mobileMode) {
        this.closeMobileDrawer();
      }
    });
  }

  toggleSidebar(): void {
    if (this.mobileMode) {
      this.mobileOpenChange.emit(!this.mobileOpen);
      return;
    }
    this.collapsedChange.emit(!this.collapsed);
  }

  closeMobileDrawer(): void {
    this.mobileOpenChange.emit(false);
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

  getIconPath(icon: string): string {
    const icons: Record<string, string> = {
      dashboard: 'M3 3h8v8H3V3zm10 0h8v5h-8V3zM3 13h5v8H3v-8zm7 4h11v4H10v-4z',
      patients: 'M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm-8 1a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm8 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4zm-8 1c-2.21 0-6 1.12-6 3.33V20h6.5v-1.67c0-1 .39-2 1.13-2.8A9.8 9.8 0 0 0 8 15z',
      list: 'M4 6h3v3H4V6zm5 0h11v3H9V6zm-5 5h3v3H4v-3zm5 0h11v3H9v-3zm-5 5h3v3H4v-3zm5 0h11v3H9v-3z',
      'plus-user': 'M15 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm-7 1a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm7 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4zM4 18h2v2h2v2H6v2H4v-2H2v-2h2v-2z',
      billing: 'M6 2h12l4 4v16H6V2zm11 1.5V7h3.5L17 3.5zM9 11h10v2H9v-2zm0 4h10v2H9v-2zm0 4h7v2H9v-2z',
      receipt: 'M7 3h10v2h3v16l-3-1.5L14 21l-3-1.5L8 21l-3-1.5V5h2V3zm2 4v2h8V7H9zm0 4v2h8v-2H9zm0 4v2h5v-2H9z',
      service: 'M12 2l1.8 3.64L18 7l-2.2 3 1 4L12 12.2 7.2 14l1-4L6 7l4.2-1.36L12 2zm-7 15h14v2H5v-2zm2 3h10v2H7v-2z',
      doctor: 'M10 2h4v4h4v4h-4v4h-4v-4H6V6h4V2zm-4 15h12v2H6v-2zm1 3h10v2H7v-2z',
      opd: 'M11 2h2v3h3v2h-3v3h-2V7H8V5h3V2zm-6 9h14v9H5v-9zm2 2v5h10v-5H7z',
      ipd: 'M3 8h18v10h-2v-2H5v2H3V8zm2 2v4h14v-4H5zm2-5h10v2H7V5z',
      lab: 'M9 2h6v2h-1v5.59l4.7 7.84A3 3 0 0 1 16.14 22H7.86a3 3 0 0 1-2.56-4.57L10 9.59V4H9V2zm2.33 9-4.3 7.17a1 1 0 0 0 .83 1.5h8.28a1 1 0 0 0 .86-1.5L12.67 11h-1.34z',
      radiology: 'M4 5h16v14H4V5zm2 2v10h12V7H6zm3 2h6v6H9V9z',
      reporting: 'M5 19h14v2H5v-2zm1-2V7h3v10H6zm5 0V3h3v14h-3zm5 0v-6h3v6h-3z',
      pharmacy: 'M8 3h8v4h4v4h-4v10H8V11H4V7h4V3zm2 2v4h4V5h-4zm0 6v8h4v-8h-4z',
      accounting: 'M5 4h14v2H5V4zm0 4h14v12H5V8zm3 3v2h8v-2H8zm0 4v2h5v-2H8z',
      admin: 'M12 2l7 4v6c0 5-3.84 9.74-7 10-3.16-.26-7-5-7-10V6l7-4zm0 3.2L7 7.94V12c0 3.77 2.63 7.46 5 7.95 2.37-.49 5-4.18 5-7.95V7.94l-5-2.74z',
      users: 'M8 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm8 0a3 3 0 1 0-3-3 3 3 0 0 0 3 3zM8 13c-2.67 0-8 1.34-8 4v3h10v-3c0-1.01.39-2.06 1.1-2.94A9.94 9.94 0 0 0 8 13zm8 0c-.99 0-2.15.13-3.27.38A5.2 5.2 0 0 1 14 17v3h10v-3c0-2.66-5.33-4-8-4z',
      shield: 'M12 2l8 4v5c0 5.25-3.44 10.06-8 11-4.56-.94-8-5.75-8-11V6l8-4zm0 3.18L6 8.18V11c0 4.02 2.49 7.83 6 8.82 3.51-.99 6-4.8 6-8.82V8.18l-6-3z',
    };
    return icons[icon] ?? icons['dashboard'];
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
