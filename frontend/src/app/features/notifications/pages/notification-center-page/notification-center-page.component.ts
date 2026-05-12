import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { HmsNotification, HmsNotificationService, NotificationListResponse } from '../../../../core/services/hms-notification.service';

@Component({
  selector: 'app-notification-center-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './notification-center-page.component.html',
  styleUrls: ['./notification-center-page.component.scss'],
})
export class NotificationCenterPageComponent {
  private readonly notifications = inject(HmsNotificationService);
  private readonly router = inject(Router);

  loading = false;
  response: NotificationListResponse = { items: [], latest: [], total: 0, unread_count: 0, action_required_count: 0, critical_count: 0 };
  filters = {
    search: '',
    status: '',
    priority: '',
    module: '',
    category: '',
    due_today: false,
    overdue: false,
    assigned_to_me: true,
  };

  constructor() {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.notifications.list({ ...this.filters, limit: 80 }).subscribe({
      next: (response) => {
        this.response = response;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  update(item: HmsNotification, status: 'read' | 'dismissed' | 'completed' | 'in_progress'): void {
    this.notifications.updateStatus(item.id, status).subscribe(() => this.load());
  }

  open(item: HmsNotification): void {
    if (item.route) void this.router.navigateByUrl(item.route);
  }

  priorityClass(item: HmsNotification): string {
    return `priority-${item.priority}`;
  }

  trackById(_: number, item: HmsNotification): string {
    return item.id;
  }
}
