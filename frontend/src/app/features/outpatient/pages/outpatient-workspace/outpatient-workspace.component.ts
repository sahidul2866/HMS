import { CommonModule, KeyValue } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { User } from '../../../../core/models/auth.models';
import { OutpatientDashboard, OutpatientReport, UnifiedOutpatientQueueItem } from '../../models/outpatient.models';
import { OutpatientService } from '../../services/outpatient.service';

type OutpatientTab = 'dashboard' | 'queue' | 'consultation' | 'reports';

@Component({
  selector: 'app-outpatient-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './outpatient-workspace.component.html',
  styleUrls: ['./outpatient-workspace.component.scss'],
})
export class OutpatientWorkspaceComponent {
  private readonly outpatient = inject(OutpatientService);
  private readonly doctorsService = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);

  readonly tab = signal<OutpatientTab>('dashboard');
  readonly tabs: OutpatientTab[] = ['dashboard', 'queue', 'consultation', 'reports'];
  filters = { visit_mode: '', doctor_id: '', status: '' };
  reportFilters = { report_type: 'queue_waiting_time', visit_mode: '', doctor_id: '', status: '' };
  doctors: User[] = [];
  dashboard: OutpatientDashboard | null = null;
  queue: UnifiedOutpatientQueueItem[] = [];
  selected: UnifiedOutpatientQueueItem | null = null;
  report: OutpatientReport | null = null;
  error = '';

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['outpatientTab'] as OutpatientTab) || 'dashboard');
      this.loadCurrentTab();
    });
    this.doctorsService.listDoctors().subscribe((rows) => (this.doctors = rows));
  }

  loadCurrentTab(): void {
    this.error = '';
    this.loadDashboard();
    if (this.tab() === 'queue' || this.tab() === 'consultation') this.loadQueue();
    if (this.tab() === 'reports') this.loadReport();
  }

  loadDashboard(): void {
    this.outpatient.dashboard(this.filters).subscribe({ next: (row) => (this.dashboard = row), error: (error) => this.showError(error) });
  }

  loadQueue(): void {
    this.outpatient.queue(this.filters).subscribe({ next: (rows) => { this.queue = rows; this.selected = this.selected || rows[0] || null; }, error: (error) => this.showError(error) });
  }

  loadReport(): void {
    this.outpatient.report(this.reportFilters).subscribe({ next: (report) => (this.report = report), error: (error) => this.showError(error) });
  }

  runAction(item: UnifiedOutpatientQueueItem, action: string): void {
    if (!item.token_id) return;
    this.outpatient.action(item.token_id, action).subscribe({
      next: (updated) => {
        this.selected = updated;
        this.loadCurrentTab();
        this.notifications.success(`Patient ${action.replace('_', ' ')}`);
      },
      error: (error) => this.showError(error),
    });
  }

  statusClass(status: string | null | undefined): string {
    return `status status-${(status || 'neutral').replaceAll('_', '-')}`;
  }

  rowValue(row: Record<string, unknown>, key: string): string {
    const value = row[key];
    return value === null || value === undefined ? '-' : String(value);
  }

  sortKeyValue(a: KeyValue<string, number>, b: KeyValue<string, number>): number {
    return b.value - a.value;
  }

  private showError(error: unknown): void {
    const anyError = error as { error?: { message?: string; detail?: string }; message?: string };
    this.error = anyError.error?.message || anyError.error?.detail || anyError.message || 'Could not complete outpatient action.';
  }
}
