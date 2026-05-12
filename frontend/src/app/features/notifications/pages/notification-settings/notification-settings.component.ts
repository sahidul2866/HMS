import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { HmsNotificationService, NotificationSetting } from '../../../../core/services/hms-notification.service';

@Component({
  selector: 'app-notification-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './notification-settings.component.html',
  styleUrls: ['./notification-settings.component.scss'],
})
export class NotificationSettingsComponent {
  private readonly notifications = inject(HmsNotificationService);

  settings: NotificationSetting[] = [];
  message = '';
  form = {
    setting_key: 'global',
    in_app: true,
    email: false,
    sms_whatsapp: false,
    sound_for_critical: true,
    mute_non_critical: false,
    medication_overdue_minutes: 15,
    critical_result_ack_minutes: 30,
    discharge_clearance_minutes: 60,
    emergency_wait_minutes: 20,
  };

  constructor() {
    this.load();
  }

  load(): void {
    this.notifications.listSettings().subscribe({
      next: (settings) => (this.settings = settings),
      error: (error) => (this.message = error?.error?.message || 'Unable to load notification settings'),
    });
  }

  save(): void {
    const { setting_key, ...setting_value } = this.form;
    this.notifications.saveSetting({ setting_key, setting_value }).subscribe({
      next: () => {
        this.message = 'Notification settings saved';
        this.load();
      },
      error: (error) => (this.message = error?.error?.message || 'Unable to save notification settings'),
    });
  }
}
