import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { interval, Subscription } from 'rxjs';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { QueueCounter, QueueSummary, QueueToken } from '../../models/queue.models';
import { QueueService } from '../../services/queue.service';

@Component({
  selector: 'app-queue-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './queue-workspace.component.html',
  styleUrls: ['./queue-workspace.component.scss'],
})
export class QueueWorkspaceComponent implements OnDestroy {
  private readonly queueService = inject(QueueService);
  private readonly notifications = inject(NotificationService);
  readonly session = inject(SessionService);
  private polling?: Subscription;

  scopes = [
    { value: 'opd', label: 'OPD' },
    { value: 'billing', label: 'Billing' },
    { value: 'pharmacy', label: 'Pharmacy' },
    { value: 'laboratory', label: 'Lab' },
    { value: 'radiology', label: 'Radiology' },
    { value: 'blood_bank', label: 'Blood Bank' },
    { value: 'er', label: 'Emergency' },
  ];
  selectedScope = 'opd';
  selectedStatus = '';
  selectedCounterId = '';
  search = '';
  displayMode = false;
  tokens: QueueToken[] = [];
  counters: QueueCounter[] = [];
  summary: QueueSummary | null = null;
  settingsMessage = '';
  counterDraft = {
    code: '',
    name: '',
    module: 'opd',
    service_area: '',
    department_name: '',
    room_number: '',
    audio_enabled: false,
    display_enabled: true,
  };
  settingDraft = {
    setting_key: 'global',
    queue_prefix: 'AUTO',
    token_format: '{prefix}-{sequence}',
    appointment_policy: 'mixed',
    waiting_alert_minutes: 30,
    auto_skip_minutes: 0,
    audio_language: 'en-US',
    audio_enabled: false,
  };

  constructor() {
    this.loadAll();
    this.polling = interval(30000).subscribe(() => this.loadTokens());
  }

  ngOnDestroy(): void {
    this.polling?.unsubscribe();
  }

  loadAll(): void {
    this.loadCounters();
    this.loadTokens();
    this.loadSummary();
  }

  loadTokens(): void {
    this.queueService
      .listTokens({
        queue_scope: this.selectedScope,
        status: this.selectedStatus,
        counter_id: this.selectedCounterId,
        search: this.search,
      })
      .subscribe((tokens) => (this.tokens = tokens));
  }

  loadCounters(): void {
    this.queueService.listCounters().subscribe((counters) => (this.counters = counters));
  }

  loadSummary(): void {
    this.queueService.summary().subscribe((summary) => (this.summary = summary));
  }

  callNext(): void {
    this.queueService.callNext({ queue_scope: this.selectedScope, counter_id: this.selectedCounterId || null }).subscribe({
      next: (token) => {
        this.notifications.success(`Called ${token.token_number}.`);
        this.loadAll();
      },
      error: (error) => this.notifications.error(error?.error?.message || 'No waiting patient found.'),
    });
  }

  update(token: QueueToken, status: string): void {
    this.queueService.updateStatus(token.id, status, this.selectedCounterId || null).subscribe(() => this.loadAll());
  }

  transfer(token: QueueToken, scope: string): void {
    this.queueService
      .transfer(token.id, {
        queue_scope: scope,
        module: scope,
        service_area: scope === 'billing' ? 'payment' : scope,
        department_name: token.department_name,
        priority: token.priority,
      })
      .subscribe(() => this.loadAll());
  }

  createCounter(): void {
    this.queueService.createCounter(this.counterDraft).subscribe({
      next: () => {
        this.notifications.success('Queue counter created.');
        this.counterDraft.code = '';
        this.counterDraft.name = '';
        this.loadCounters();
      },
      error: (error) => this.notifications.error(error?.error?.message || 'Unable to create counter.'),
    });
  }

  saveSettings(): void {
    const { setting_key, ...setting_value } = this.settingDraft;
    this.queueService.saveSetting({ setting_key, setting_value }).subscribe({
      next: () => (this.settingsMessage = 'Queue settings saved.'),
      error: (error) => (this.settingsMessage = error?.error?.message || 'Unable to save queue settings.'),
    });
  }

  statusClass(token: QueueToken): string {
    return `status-${token.status}`;
  }

  priorityClass(token: QueueToken): string {
    return `priority-${token.priority}`;
  }

  trackById(_: number, token: QueueToken): string {
    return token.id;
  }
}
