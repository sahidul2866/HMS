import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { NotificationService } from '../../core/services/notification.service';
import { SessionService } from '../../core/services/session.service';
import { TabService } from '../../core/services/tab.service';
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
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  sidebarCollapsed = false;

  logout(): void {
    this.authService.logout().subscribe(() => this.notificationService.info('Logged out.'));
  }
}
