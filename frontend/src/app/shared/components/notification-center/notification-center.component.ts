import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, OnDestroy, OnInit, Renderer2, inject } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';
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
  private readonly elementRef = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly renderer = inject(Renderer2);
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
    this.subscription.add(
      this.router.events.subscribe((event) => {
        if (event instanceof NavigationStart) this.close();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
    this.renderer.removeClass(document.body, 'notification-center-open');
  }

  toggle(): void {
    this.open = !this.open;
    this.syncOpenLayer();
    if (this.open) this.refresh();
  }

  close(): void {
    if (!this.open) return;
    this.open = false;
    this.syncOpenLayer();
  }

  @HostListener('document:pointerdown', ['$event'])
  onDocumentPointerDown(event: PointerEvent): void {
    if (!this.open || this.elementRef.nativeElement.contains(event.target as Node)) return;
    this.close();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
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

  private syncOpenLayer(): void {
    if (this.open) {
      this.renderer.addClass(document.body, 'notification-center-open');
      return;
    }
    this.renderer.removeClass(document.body, 'notification-center-open');
  }

  priorityClass(item: HmsNotification): string {
    return `priority-${item.priority}`;
  }

  trackById(_: number, item: HmsNotification): string {
    return item.id;
  }
}
