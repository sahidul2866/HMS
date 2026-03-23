import { CommonModule } from '@angular/common';
import { Component, HostListener, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

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
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);

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

  private syncViewport(): void {
    this.isMobileViewport = window.innerWidth <= 960;
    if (!this.isMobileViewport) {
      this.mobileSidebarOpen = false;
    }
  }
}
