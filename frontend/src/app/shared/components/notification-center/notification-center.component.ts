import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { NotificationItem, NotificationLevel, NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-notification-center',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './notification-center.component.html',
})
export class NotificationCenterComponent {
  readonly notificationService = inject(NotificationService);

  getTitle(level: NotificationLevel): string {
    switch (level) {
      case 'success':
        return 'Success';
      case 'error':
        return 'Action Failed';
      case 'warning':
        return 'Attention';
      default:
        return 'Information';
    }
  }

  getIcon(item: NotificationItem): string {
    switch (item.level) {
      case 'success':
        return '✓';
      case 'error':
        return '!';
      case 'warning':
        return '!';
      default:
        return 'i';
    }
  }

  getAgeLabel(item: NotificationItem): string {
    const seconds = Math.max(0, Math.floor((Date.now() - item.createdAt) / 1000));
    if (seconds < 5) {
      return 'Just now';
    }
    if (seconds < 60) {
      return `${seconds}s ago`;
    }
    return `${Math.floor(seconds / 60)}m ago`;
  }

  dismiss(id: number): void {
    this.notificationService.dismiss(id);
  }
}
