import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-notification-center',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './notification-center.component.html',
})
export class NotificationCenterComponent {
  readonly notificationService = inject(NotificationService);

  dismiss(id: number): void {
    this.notificationService.dismiss(id);
  }
}
