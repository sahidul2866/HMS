import { CommonModule } from '@angular/common';
import { Component, HostListener, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';

import { PERMISSIONS } from '../../core/constants/permissions';
import { AuthService } from '../../core/services/auth.service';
import { NotificationService } from '../../core/services/notification.service';
import { SessionService } from '../../core/services/session.service';
import { TabService } from '../../core/services/tab.service';
import { ThemeService } from '../../core/services/theme.service';
import { SidebarComponent } from '../../navigation/sidebar/sidebar.component';
import { TabStripComponent } from '../../shared/components/tab-strip/tab-strip.component';

@Component({
  selector: 'app-app-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, SidebarComponent, TabStripComponent],
  templateUrl: './app-layout.component.html',
  styleUrl: './app-layout.component.scss',
})
export class AppLayoutComponent {
  readonly sessionService = inject(SessionService);
  readonly tabService = inject(TabService);
  readonly themeService = inject(ThemeService);
  readonly quickActions = [
    { label: 'New Bill', route: '/billing/create', permissions: [PERMISSIONS.billingInvoiceCreate], tone: 'primary' },
    { label: 'Due', route: '/billing/due-payments', permissions: [PERMISSIONS.billingInvoiceCreate] },
    { label: 'OPD', route: '/opd/register', permissions: [PERMISSIONS.opdView] },
    { label: 'IPD', route: '/ipd/admit', permissions: [PERMISSIONS.ipdAdmissionManage] },
    { label: 'Diagnostics', route: '/diagnostics/orders', permissions: [PERMISSIONS.laboratoryView] },
    { label: 'Pharmacy Sale', route: '/pharmacy/sales', permissions: [PERMISSIONS.pharmacyView] },
  ];
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  sidebarCollapsed = false;
  mobileSidebarOpen = false;
  isMobileViewport = false;

  constructor() {
    this.syncViewport();
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    this.syncViewport();
  }

  toggleMobileSidebar(): void {
    this.mobileSidebarOpen = !this.mobileSidebarOpen;
  }

  closeMobileSidebar(): void {
    this.mobileSidebarOpen = false;
  }

  logout(): void {
    this.authService.logout().subscribe(() => this.notificationService.info('Logged out.'));
  }

  visibleQuickActions(): typeof this.quickActions {
    return this.quickActions.filter((action) => this.sessionService.hasPermission(action.permissions));
  }

  isQuickActionActive(route: string): boolean {
    return this.router.url.startsWith(route);
  }

  navigate(route: string): void {
    this.router.navigateByUrl(route);
    this.closeMobileSidebar();
  }

  private syncViewport(): void {
    this.isMobileViewport = window.innerWidth <= 960;
    if (!this.isMobileViewport) {
      this.mobileSidebarOpen = false;
    }
  }
}
