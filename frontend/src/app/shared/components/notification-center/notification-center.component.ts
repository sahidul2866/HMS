import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription, interval, startWith, switchMap } from 'rxjs';

import { HmsNotification, HmsNotificationService, NotificationSummary } from '../../../core/services/hms-notification.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SessionService } from '../../../core/services/session.service';

@Component({
  selector: 'app-notification-center',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './notification-center.component.html',
  styleUrls: ['./notification-center.component.scss'],
})
export class NotificationCenterComponent implements OnInit, OnDestroy {
  private readonly notifications = inject(HmsNotificationService);
  private readonly router = inject(Router);
  private readonly toast = inject(NotificationService);
  readonly session = inject(SessionService);
  private subscription?: Subscription;

  open = false;
  loading = false;
  summary: NotificationSummary = { unread_count: 0, action_required_count: 0, critical_count: 0, latest: [] };

  ngOnInit(): void {
    if (!this.session.hasPermission('notification.view')) return;
    this.subscription = interval(45000)
      .pipe(
        startWith(0),
        switchMap(() => this.notifications.summary())
      )
      .subscribe({
        next: (summary) => {
          const hadCritical = this.summary.critical_count;
          this.summary = summary;
          if (summary.critical_count > hadCritical && hadCritical > 0) {
            this.toast.error('Critical notification received.');
          }
        },
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  toggle(): void {
    this.open = !this.open;
    if (this.open) this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.notifications.summary().subscribe({
      next: (summary) => {
        this.summary = summary;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  markRead(item: HmsNotification, event?: Event): void {
    event?.stopPropagation();
    this.notifications.updateStatus(item.id, 'read').subscribe(() => this.refresh());
  }

  dismiss(item: HmsNotification, event?: Event): void {
    event?.stopPropagation();
    this.notifications.updateStatus(item.id, 'dismissed').subscribe(() => this.refresh());
  }

  complete(item: HmsNotification, event?: Event): void {
    event?.stopPropagation();
    this.notifications.updateStatus(item.id, 'completed').subscribe(() => this.refresh());
  }

  markAllRead(): void {
    this.notifications.markAllRead().subscribe(() => this.refresh());
  }

  openNotification(item: HmsNotification): void {
    if (item.status === 'unread') this.markRead(item);
    if (item.route) {
      void this.router.navigateByUrl(item.route);
      this.open = false;
    }
  }

  openFullCenter(): void {
    void this.router.navigateByUrl('/notifications');
    this.open = false;
  }

  priorityClass(item: HmsNotification): string {
    return `priority-${item.priority}`;
  }

  trackById(_: number, item: HmsNotification): string {
    return item.id;
  }
}
