import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { FloatingAssistantComponent } from '../../../../shared/components/floating-assistant/floating-assistant.component';
import { OPDSummary, OPDVisit } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

type DashboardKPI = {
  label: string;
  value: string;
  detail: string;
  tone: string;
};

type DashboardBar = {
  label: string;
  value: number;
  detail: string;
  width: string;
  tone: string;
};

@Component({
  selector: 'app-opd-overview',
  standalone: true,
  imports: [CommonModule, FloatingAssistantComponent],
  templateUrl: './opd-overview.component.html',
  styleUrls: ['./opd-overview.component.scss'],
})
export class OPDOverviewComponent {
  private readonly opdService = inject(OPDService);
  private readonly router = inject(Router);

  summary: OPDSummary | null = null;
  visits: OPDVisit[] = [];
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
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.opdService.getSummary(null).subscribe((summary) => (this.summary = summary));
    this.opdService.listVisits(null).subscribe((visits) => (this.visits = visits));
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  navigateToVisitList(): void {
    void this.router.navigate(['/opd/visits']);
  }

  get dashboardKpis(): DashboardKPI[] {
    const totalVisits = this.summary?.total_visits ?? this.visits.length;
    const waitingVisits = this.summary?.waiting_visits ?? this.getVisitCountByStatus('waiting');
    const consultationVisits = this.summary?.in_consultation_visits ?? this.getVisitCountByStatus('in_consultation');
    const completedVisits = this.summary?.completed_visits ?? this.getVisitCountByStatus('completed');

    return [
      { label: 'Today Visits', value: String(totalVisits), detail: `${this.getPaidVisitsCount()} paid registrations`, tone: 'teal' },
      { label: 'Collected', value: this.formatCurrency(this.getCollectedAmount()), detail: `${this.getPaidVisitsCount()} settled visits`, tone: 'emerald' },
      { label: 'Outstanding', value: this.formatCurrency(this.getOutstandingAmount()), detail: `${this.getUnpaidVisitsCount()} visits need payment`, tone: 'amber' },
      { label: 'In Queue', value: String(waitingVisits + consultationVisits), detail: `${waitingVisits} waiting · ${consultationVisits} in consultation`, tone: 'blue' },
      { label: 'Completed', value: String(completedVisits), detail: `${this.getCompletionRate()} completion rate`, tone: 'slate' },
      { label: 'Avg Visit Value', value: this.formatCurrency(this.getAverageVisitValue()), detail: `${this.getTotalOrderCount()} total clinical orders`, tone: 'rose' },
    ];
  }

  get statusChartItems(): DashboardBar[] {
    const items = [
      { label: 'Waiting', value: this.summary?.waiting_visits ?? this.getVisitCountByStatus('waiting'), tone: 'var(--chart-teal)' },
      { label: 'In Consultation', value: this.summary?.in_consultation_visits ?? this.getVisitCountByStatus('in_consultation'), tone: 'var(--chart-blue)' },
      { label: 'Completed', value: this.summary?.completed_visits ?? this.getVisitCountByStatus('completed'), tone: 'var(--chart-emerald)' },
      { label: 'Prescribed', value: this.getVisitCountByStatus('prescribed'), tone: 'var(--chart-gold)' },
      { label: 'Billed', value: this.getVisitCountByStatus('billed'), tone: 'var(--chart-violet)' },
    ];
    const max = Math.max(...items.map((item) => item.value), 1);
    return items.map((item) => ({
      ...item,
      detail: this.getShareLabel(item.value, this.summary?.total_visits ?? this.visits.length),
      width: `${Math.max((item.value / max) * 100, item.value > 0 ? 12 : 0)}%`,
    }));
  }

  get doctorLoadItems(): DashboardBar[] {
    const counts = new Map<string, number>();
    for (const visit of this.visits) {
      const label = visit.consulting_doctor_name || 'Unassigned';
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }

    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5);
    const max = Math.max(...sorted.map(([, value]) => value), 1);

    return sorted.map(([label, value]) => ({
      label,
      value,
      detail: this.getShareLabel(value, this.visits.length),
      width: `${Math.max((value / max) * 100, value > 0 ? 14 : 0)}%`,
      tone: 'var(--chart-blue)',
    }));
  }

  get orderMixItems(): DashboardBar[] {
    const items = [
      { label: 'Prescription', value: this.getOrderCountByType('prescription'), tone: 'var(--chart-gold)' },
      { label: 'Investigation', value: this.getOrderCountByType('investigation'), tone: 'var(--chart-rose)' },
      { label: 'Procedure', value: this.getOrderCountByType('procedure'), tone: 'var(--chart-violet)' },
    ];
    const max = Math.max(...items.map((item) => item.value), 1);
    const total = items.reduce((sum, item) => sum + item.value, 0);

    return items.map((item) => ({
      ...item,
      detail: total ? this.getShareLabel(item.value, total) : 'No orders yet',
      width: `${Math.max((item.value / max) * 100, item.value > 0 ? 18 : 0)}%`,
    }));
  }

  get revenueHighlights(): Array<{ label: string; value: string }> {
    return [
      { label: 'Gross Fees', value: this.formatCurrency(this.getGrossAmount()) },
      { label: 'Discounts', value: this.formatCurrency(this.getDiscountAmount()) },
      { label: 'Net Collection', value: this.formatCurrency(this.getCollectedAmount()) },
    ];
  }

  get revenueHeadline(): string {
    return this.formatCurrency(this.getCollectedAmount());
  }

  get weeklyTrendItems(): DashboardBar[] {
    const today = new Date();
    const points: Array<{ key: string; label: string }> = [];
    for (let offset = 6; offset >= 0; offset -= 1) {
      const date = new Date(today);
      date.setDate(today.getDate() - offset);
      points.push({ key: date.toISOString().slice(0, 10), label: date.toLocaleDateString('en-US', { weekday: 'short' }) });
    }

    const counts = new Map<string, number>();
    for (const visit of this.visits) {
      counts.set(visit.visit_date, (counts.get(visit.visit_date) ?? 0) + 1);
    }

    const max = Math.max(...points.map((point) => counts.get(point.key) ?? 0), 1);
    return points.map((point) => {
      const value = counts.get(point.key) ?? 0;
      return {
        label: point.label,
        value,
        detail: point.key,
        width: `${Math.max((value / max) * 100, value > 0 ? 12 : 8)}%`,
        tone: 'var(--chart-teal)',
      };
    });
  }

  private getVisitCountByStatus(status: string): number {
    return this.visits.filter((visit) => visit.status === status).length;
  }

  private getOrderCountByType(orderType: string): number {
    return this.visits.reduce((sum, visit) => sum + visit.orders.filter((order) => order.order_type === orderType).length, 0);
  }

  private getTotalOrderCount(): number {
    return this.visits.reduce((sum, visit) => sum + visit.orders.length, 0);
  }

  private getPaidVisitsCount(): number {
    return this.visits.filter((visit) => (visit.consultation_payment_status || '').toLowerCase() === 'paid').length;
  }

  private getUnpaidVisitsCount(): number {
    return this.visits.filter((visit) => (visit.consultation_payment_status || '').toLowerCase() !== 'paid').length;
  }

  private getGrossAmount(): number {
    return this.visits.reduce((sum, visit) => sum + Number(visit.consultation_total ?? visit.consultation_fee ?? 0), 0);
  }

  private getDiscountAmount(): number {
    return this.visits.reduce((sum, visit) => sum + Number(visit.consultation_discount ?? 0), 0);
  }

  private getCollectedAmount(): number {
    return this.visits
      .filter((visit) => (visit.consultation_payment_status || '').toLowerCase() === 'paid')
      .reduce((sum, visit) => sum + Number(visit.consultation_total ?? visit.consultation_fee ?? 0), 0);
  }

  private getOutstandingAmount(): number {
    return Math.max(this.getGrossAmount() - this.getCollectedAmount(), 0);
  }

  private getAverageVisitValue(): number {
    return this.visits.length ? this.getGrossAmount() / this.visits.length : 0;
  }

  private getCompletionRate(): string {
    const total = this.summary?.total_visits ?? this.visits.length;
    const completed = this.summary?.completed_visits ?? this.getVisitCountByStatus('completed');
    return total ? `${Math.round((completed / total) * 100)}%` : '0%';
  }

  private getShareLabel(value: number, total: number): string {
    if (!total) return '0%';
    return `${Math.round((value / total) * 100)}% share`;
  }

  private formatCurrency(value: number): string {
    return `BDT ${value.toFixed(2)}`;
  }
}
