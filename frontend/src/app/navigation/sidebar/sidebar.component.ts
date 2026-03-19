import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

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
  items: MenuItem[] = [];

  constructor() {
    this.sessionService.state$.subscribe(() => {
      this.items = menuConfig.filter((item) => this.sessionService.hasPermission(item.permissions));
    });
  }
}
