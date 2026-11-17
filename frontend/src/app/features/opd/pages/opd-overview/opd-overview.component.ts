import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Params, Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { FloatingAssistantComponent } from '../../../../shared/components/floating-assistant/floating-assistant.component';
import { OPDSummary } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

type DashboardKPI = {
  label: string;
  value: string;
  detail: string;
  tone: string;
  /** Visit List filters this card opens. */
  query: Params;
};

type DashboardBar = {
  label: string;
  value: number;
  detail: string;
  width: string;
  tone: string;
};

const REFRESH_MS = 60_000;

@Component({
  selector: 'app-opd-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, FloatingAssistantComponent],
  templateUrl: './opd-overview.component.html',
  styleUrls: ['./opd-overview.component.scss'],
})
export class OPDOverviewComponent implements OnDestroy {
  private readonly opdService = inject(OPDService);
  private readonly doctorDirectory = inject(DoctorDirectoryService);
  private readonly router = inject(Router);
  private readonly timer = window.setInterval(() => this.loadDashboard(true), REFRESH_MS);

  summary: OPDSummary | null = null;
  loading = true;
  error = '';
  doctors: User[] = [];
  /** Empty means "today" on the hospital clock. */
  selectedDate = '';
  selectedDoctorId = '';
  readonly assistantQuickActions = [
    'Show today’s OPD patients',
    'Show waiting OPD patients',
    'Show my OPD appointments',
    'Book OPD appointment',
    'Check patient due by patient ID',
    'Show revenue analysis',
    'Which doctor is available now?',
    'How many OPD patients today?',
  ];

  constructor() {
    this.doctorDirectory.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.loadDashboard();
  }

  ngOnDestroy(): void {
    window.clearInterval(this.timer);
  }

  loadDashboard(background = false): void {
    if (!background) this.loading = true;
    this.opdService.getSummary(this.selectedDoctorId || null, this.selectedDate || null, background).subscribe({
      next: (summary) => {
        this.summary = summary;
        this.error = '';
        this.loading = false;
      },
      error: (error) => {
        // A refused read must not look like a quiet day: say why the numbers are missing.
        this.loading = false;
        if (!background) {
          this.summary = null;
          this.error = error?.error?.error?.message || 'The OPD figures could not be loaded. Try again shortly.';
        }
      },
    });
  }

  shiftDay(days: number): void {
    const base = this.summary?.summary_date ?? this.today;
    const next = new Date(`${base}T00:00:00`);
    next.setDate(next.getDate() + days);
    const value = this.localIso(next);
    this.selectedDate = value >= this.today ? '' : value;
    this.loadDashboard();
  }

  goToday(): void {
    this.selectedDate = '';
    this.loadDashboard();
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  navigateToQueue(): void {
    void this.router.navigate(['/opd/queue']);
  }

  navigateToVisitList(query: Params = {}): void {
    void this.router.navigate(['/opd/visits'], { queryParams: { date: this.summary?.summary_date ?? this.today, ...query } });
  }

  openVisit(visitId: string): void {
    void this.router.navigate(['/opd/visits'], { queryParams: { openVisit: visitId } });
  }

  /** Hospital-clock calendar date, which the server uses for "today". */
  get today(): string {
    return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Dhaka' });
  }

  get isToday(): boolean {
    return !this.summary?.summary_date || this.summary.summary_date === this.today;
  }

  get dayLabel(): string {
    return this.isToday ? 'today' : `on ${this.formatDay(this.summary?.summary_date ?? '', true)}`;
  }

  get lastUpdated(): string {
    return this.summary?.as_of ? new Date(this.summary.as_of).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Dhaka' }) : '';
  }

  get hasNoVisits(): boolean {
    return !!this.summary && this.summary.total_visits === 0;
  }

  get dashboardKpis(): DashboardKPI[] {
    const s = this.summary;
    if (!s) return [];
    const billedVisits = Math.max(s.total_visits - (s.cancelled_visits ?? 0) - (s.not_billed_visits ?? 0), 0);
    const owing = s.visits_with_balance ?? 0;
    const notBilled = s.not_billed_visits ?? 0;
    const prescribed = s.prescribed_visits ?? 0;
    const inQueue = s.waiting_visits + s.in_consultation_visits;
    return [
      {
        label: `Registered ${this.dayLabel}`,
        value: String(s.total_visits),
        detail: s.total_visits ? [`${s.paid_visits ?? 0} paid`, `${owing} with a balance`, `${notBilled} not billed yet`, s.cancelled_visits ? `${s.cancelled_visits} cancelled` : ''].filter(Boolean).join(' · ') : 'No registrations yet',
        tone: 'teal',
        query: {},
      },
      {
        label: 'Collected',
        value: this.formatCurrency(s.collected_amount),
        detail: `of ${this.formatCurrency(s.billed_amount)} billed ${this.dayLabel}`,
        tone: 'emerald',
        query: { payment: 'paid' },
      },
      {
        label: 'Outstanding',
        value: this.formatCurrency(s.outstanding_amount),
        detail: owing ? `${owing} visit${owing === 1 ? '' : 's'} with a balance${notBilled ? ` · ${notBilled} not billed yet` : ''}` : notBilled ? `Nothing owed yet · ${notBilled} visit${notBilled === 1 ? '' : 's'} not billed` : 'Nothing owed',
        tone: 'amber',
        query: { payment: 'due' },
      },
      {
        label: 'In queue',
        value: String(inQueue),
        detail: `${s.waiting_visits} waiting · ${s.in_consultation_visits} in consultation${prescribed ? ` · ${prescribed} post-consultation` : ''}`,
        tone: 'blue',
        query: { status: s.waiting_visits || !s.in_consultation_visits ? 'waiting' : 'in_consultation' },
      },
      {
        label: 'Completed',
        value: String(s.completed_visits),
        detail: `${this.rate(s.completed_visits, s.total_visits - (s.cancelled_visits ?? 0))} of active visits${prescribed ? ` · ${prescribed} prescribed, not closed` : ''}`,
        tone: 'slate',
        query: { status: 'completed' },
      },
      {
        label: 'Average bill',
        value: this.formatCurrency(billedVisits ? Number(s.billed_amount ?? 0) / billedVisits : 0),
        detail: `${this.totalOrders} clinical order${this.totalOrders === 1 ? '' : 's'} · per billed visit`,
        tone: 'rose',
        query: {},
      },
    ];
  }

  get statusChartItems(): DashboardBar[] {
    const s = this.summary;
    if (!s) return [];
    const known = s.waiting_visits + s.in_consultation_visits + (s.prescribed_visits ?? 0) + s.completed_visits + (s.cancelled_visits ?? 0);
    const items = [
      { label: 'Waiting', value: s.waiting_visits, tone: 'var(--chart-teal)', note: '' },
      { label: 'In consultation', value: s.in_consultation_visits, tone: 'var(--chart-blue)', note: '' },
      { label: 'Post-consultation', value: s.prescribed_visits ?? 0, tone: 'var(--chart-gold)', note: 'prescribed, not yet closed' },
      { label: 'Completed', value: s.completed_visits, tone: 'var(--chart-emerald)', note: '' },
      { label: 'Cancelled', value: s.cancelled_visits ?? 0, tone: 'var(--chart-rose)', note: '' },
      { label: 'Other', value: Math.max(s.total_visits - known, 0), tone: 'var(--chart-violet)', note: '' },
    ].filter((item) => item.label !== 'Other' || item.value > 0);
    return this.bars(items, s.total_visits, (item) => [this.share(item.value, s.total_visits), item.note].filter(Boolean).join(' · '));
  }

  get doctorLoadItems(): DashboardBar[] {
    const rows = (this.summary?.doctor_load ?? []).slice(0, 5);
    const assigned = (this.summary?.doctor_load ?? []).reduce((sum, row) => sum + row.visits, 0);
    return this.bars(rows.map((row) => ({ label: row.doctor_name, value: row.visits, tone: 'var(--chart-blue)' })), assigned, (item) => `${item.value} visit${item.value === 1 ? '' : 's'} · ${this.share(item.value, assigned)} of doctor-assigned visits`);
  }

  get unassignedNote(): string {
    const count = this.summary?.unassigned_visits ?? 0;
    return count ? `${count} visit${count === 1 ? ' was' : 's were'} registered through the billing desk without a doctor and ${count === 1 ? 'is' : 'are'} not counted above.` : '';
  }

  get orderMixItems(): DashboardBar[] {
    const s = this.summary;
    const items = [
      { label: 'Prescription', value: s?.prescription_orders ?? 0, tone: 'var(--chart-gold)' },
      { label: 'Investigation', value: s?.investigation_orders ?? 0, tone: 'var(--chart-rose)' },
      { label: 'Procedure', value: s?.procedure_orders ?? 0, tone: 'var(--chart-violet)' },
    ];
    const total = items.reduce((sum, item) => sum + item.value, 0);
    return this.bars(items, total, (item) => (total ? this.share(item.value, total) : 'No orders yet'));
  }

  get totalOrders(): number {
    const s = this.summary;
    return (s?.prescription_orders ?? 0) + (s?.investigation_orders ?? 0) + (s?.procedure_orders ?? 0);
  }

  get revenueHighlights(): Array<{ label: string; value: string }> {
    const s = this.summary;
    return [
      { label: 'Gross fees', value: this.formatCurrency(s?.gross_amount) },
      { label: 'Discounts', value: this.formatCurrency(s?.discount_amount) },
      { label: 'Billed (net)', value: this.formatCurrency(s?.billed_amount) },
      { label: 'Collected', value: this.formatCurrency(s?.collected_amount) },
      { label: 'Outstanding', value: this.formatCurrency(s?.outstanding_amount) },
    ];
  }

  get revenueHeadline(): string {
    return this.formatCurrency(this.summary?.collected_amount);
  }

  get weeklyTrendItems(): DashboardBar[] {
    const points = this.summary?.daily_visits ?? [];
    const max = Math.max(...points.map((point) => point.visits), 1);
    const last = points.length - 1;
    return points.map((point, index) => ({
      label: index === last && this.isToday ? 'Today' : this.formatDay(point.day),
      value: point.visits,
      detail: point.day,
      width: `${Math.max((point.visits / max) * 100, point.visits > 0 ? 12 : 8)}%`,
      tone: index === last ? 'var(--chart-emerald)' : 'var(--chart-teal)',
    }));
  }

  get trendRange(): string {
    const points = this.summary?.daily_visits ?? [];
    return points.length ? `${this.formatDay(points[0].day, true)} – ${this.formatDay(points[points.length - 1].day, true)}` : '';
  }

  paymentLabel(status: string): string {
    return ({ paid: 'Paid', partial: 'Part paid', unpaid: 'Unpaid', returned: 'Returned' } as Record<string, string>)[status] ?? status;
  }

  private bars<T extends { label: string; value: number; tone: string }>(items: T[], total: number, detail: (item: T) => string): DashboardBar[] {
    const max = Math.max(...items.map((item) => item.value), 1);
    return items.map((item) => ({ label: item.label, value: item.value, tone: item.tone, detail: detail(item), width: `${Math.max((item.value / max) * 100, item.value > 0 ? 12 : 0)}%` }));
  }

  private share(value: number, total: number): string {
    return total ? `${Math.round((value / total) * 100)}%` : '0%';
  }

  private rate(value: number, total: number): string {
    return total > 0 ? `${Math.round((value / total) * 100)}%` : '0%';
  }

  private formatDay(iso: string, withYear = false): string {
    if (!iso) return '';
    return new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', withYear ? { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' } : { weekday: 'short', day: 'numeric', month: 'short' });
  }

  private localIso(date: Date): string {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  private formatCurrency(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2 }).format(Number(value ?? 0));
  }
}
