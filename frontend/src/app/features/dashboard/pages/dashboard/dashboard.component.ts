import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { SessionService } from '../../../../core/services/session.service';
import { DashboardAnalytics, DashboardKpi, DashboardPoint } from '../../models/dashboard-analytics.models';
import { DashboardAnalyticsService, DashboardFilters } from '../../services/dashboard-analytics.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, HasPermissionDirective],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent {
  readonly session = inject(SessionService);
  private readonly analyticsService = inject(DashboardAnalyticsService);

  loading = true;
  error = '';
  analytics: DashboardAnalytics | null = null;
  filters: DashboardFilters = {
    date_from: this.relativeDate(-29),
    date_to: this.relativeDate(0),
    department: '',
    patient_type: '',
    payment_status: '',
    module_type: '',
  };

  constructor() {
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    this.loading = true;
    this.error = '';
    this.analyticsService.getAnalytics(this.filters).subscribe({
      next: (analytics) => {
        this.analytics = analytics;
        this.loading = false;
      },
      error: (error) => {
        this.error = error?.error?.message || error?.error?.detail || 'Dashboard analytics could not be loaded.';
        this.loading = false;
      },
    });
  }

  formatKpi(kpi: DashboardKpi): string {
    if (kpi.format === 'money') {
      return this.formatMoney(kpi.value);
    }
    return new Intl.NumberFormat('en-BD').format(kpi.value);
  }

  formatMoney(value: number | string | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  max(points: DashboardPoint[] | undefined): number {
    return Math.max(...(points || []).map((point) => Number(point.value || 0)), 1);
  }

  total(points: DashboardPoint[] | undefined): number {
    return (points || []).reduce((sum, point) => sum + Number(point.value || 0), 0);
  }

  donutStyle(points: DashboardPoint[] | undefined): string {
    const rows = points || [];
    const sum = this.total(rows) || 1;
    const colors = ['#0f766e', '#2563eb', '#f59e0b', '#dc2626', '#7c3aed', '#14b8a6'];
    let cursor = 0;
    const stops = rows.map((point, index) => {
      const start = cursor;
      cursor += (Number(point.value || 0) / sum) * 100;
      return `${colors[index % colors.length]} ${start}% ${cursor}%`;
    });
    return `conic-gradient(${stops.join(', ') || '#e2e8f0 0 100%'})`;
  }

  sparkline(points: number[]): string {
    const max = Math.max(...points, 1);
    return points.map((value, index) => `${(index / Math.max(points.length - 1, 1)) * 100},${100 - (value / max) * 85}`).join(' ');
  }

  trendClass(value: number): string {
    if (value > 0) return 'trend-up';
    if (value < 0) return 'trend-down';
    return 'trend-flat';
  }

  printDashboard(): void {
    window.print();
  }

  exportDashboard(): void {
    if (!this.analytics) return;
    const rows = this.analytics.kpis.map((kpi) => [kpi.title, kpi.value, kpi.description, kpi.trend].join(','));
    const blob = new Blob([['Metric,Value,Description,Trend', ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'hospital-dashboard-summary.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  private relativeDate(offset: number): string {
    const date = new Date();
    date.setDate(date.getDate() + offset);
    return date.toISOString().slice(0, 10);
  }
}
