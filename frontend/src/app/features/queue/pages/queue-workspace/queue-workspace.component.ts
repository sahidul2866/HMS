import { CommonModule } from '@angular/common';
import { Component, HostListener, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { interval, Subscription } from 'rxjs';

import { NotificationService } from '../../../../core/services/notification.service';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { User } from '../../../../core/models/auth.models';
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
  private readonly route = inject(ActivatedRoute);
  private readonly doctorDirectory = inject(DoctorDirectoryService);
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
  selectedDoctorId = '';
  search = '';
  displayMode = false;
  tokens: QueueToken[] = [];
  counters: QueueCounter[] = [];
  summary: QueueSummary | null = null;
  doctors: User[] = [];
  readonly opdMode = this.route.snapshot.data['queueScope'] === 'opd';
  settingsMessage = '';
  counterDraft = {
    code: '',
    name: '',
    module: 'opd',
    service_area: '',
    department_name: '',
    room_number: '',
    doctor_user_id: '',
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
    auto_call_next: true,
    late_grace_minutes: 15,
    recall_limit: 2,
  };

  constructor() {
    if (this.opdMode) this.selectedScope = 'opd';
    this.doctorDirectory.listDoctors().subscribe((doctors) => (this.doctors = doctors));
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
        doctor_user_id: this.selectedDoctorId,
      })
      .subscribe((tokens) => (this.tokens = tokens));
  }

  loadCounters(): void {
    this.queueService.listCounters(this.opdMode ? 'opd' : undefined).subscribe((counters) => (this.counters = counters));
  }

  loadSummary(): void {
    this.queueService.summary({ queue_scope: this.opdMode ? 'opd' : this.selectedScope, doctor_user_id: this.selectedDoctorId }).subscribe((summary) => (this.summary = summary));
  }

  callNext(): void {
    if (this.selectedScope === 'opd' && !this.selectedDoctorId && !this.selectedCounterId) {
      this.notifications.warning('Select a doctor or doctor counter first.');
      return;
    }
    this.queueService.callNext({ queue_scope: this.selectedScope, counter_id: this.selectedCounterId || null, doctor_user_id: this.selectedDoctorId || null }).subscribe({
      next: (token) => {
        this.notifications.success(`Called ${token.token_number}.`);
        this.loadAll();
      },
      error: (error) => this.notifications.error(error?.error?.message || 'No waiting patient found.'),
    });
  }

  update(token: QueueToken, status: string): void {
    this.queueService.updateStatus(token.id, status, this.selectedCounterId || null).subscribe({
      next: () => {
        this.notifications.success(status === 'completed' && token.queue_scope === 'opd' ? `${token.token_number} completed. The next patient was called automatically.` : `${token.token_number} updated.`);
        this.loadAll();
      },
      error: (error) => this.notifications.error(error?.error?.error?.message || error?.error?.message || 'Unable to update queue token.'),
    });
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

  setPriority(token: QueueToken, priority: 'urgent' | 'normal'): void {
    const reason = window.prompt(`Reason for changing ${token.token_number} to ${priority}:`)?.trim();
    if (!reason) return;
    this.queueService.updatePriority(token.id, priority, reason).subscribe(() => this.loadAll());
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

  onScopeChanged(): void {
    this.selectedDoctorId = '';
    this.selectedCounterId = '';
    this.loadAll();
  }

  onDoctorChanged(): void {
    this.selectedCounterId = '';
    this.loadTokens();
    this.loadSummary();
  }

  onCounterChanged(): void {
    const counter = this.counters.find((item) => item.id === this.selectedCounterId);
    if (counter?.doctor_user_id) this.selectedDoctorId = counter.doctor_user_id;
    this.loadTokens();
    this.loadSummary();
  }

  setCounterStatus(status: 'active' | 'paused'): void {
    if (!this.selectedCounterId) {
      this.notifications.warning('Select a counter first.');
      return;
    }
    this.queueService.updateCounterStatus(this.selectedCounterId, status).subscribe(() => {
      this.notifications.success(`Queue counter ${status}.`);
      this.loadAll();
    });
  }

  canShowAction(token: QueueToken, action: string): boolean {
    const allowed: Record<string, string[]> = {
      called: ['waiting', 'registered', 'recalled', 'skipped'],
      in_progress: ['called', 'recalled', 'waiting'],
      completed: ['in_progress'],
      skipped: ['waiting', 'called', 'recalled'],
      recalled: ['skipped'],
    };
    return (allowed[action] || []).includes(token.status);
  }

  get currentTokens(): QueueToken[] {
    return this.tokens.filter((token) => ['called', 'in_progress'].includes(token.status));
  }

  get nextTokens(): QueueToken[] {
    return this.tokens.filter((token) => ['waiting', 'registered', 'recalled'].includes(token.status)).slice(0, 8);
  }

  doctorName(doctorId?: string | null): string {
    return this.doctors.find((doctor) => doctor.id === doctorId)?.full_name || 'Unassigned doctor';
  }

  @HostListener('window:hms:data-refresh-request', ['$event'])
  onDataRefresh(event: CustomEvent): void {
    const modules = event.detail?.modules || [];
    if (modules.includes('queue') || modules.includes('opd') || modules.includes('appointments')) this.loadAll();
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
