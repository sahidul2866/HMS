import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { RoleExperienceService, RoleExperience, RoleMetric } from '../../../../core/services/role-experience.service';
import { SessionService } from '../../../../core/services/session.service';
import { DashboardAnalytics, DashboardKpi, DashboardPoint } from '../../models/dashboard-analytics.models';
import { DashboardAnalyticsService, DashboardFilters } from '../../services/dashboard-analytics.service';

interface RoleDashboardCard {
  label: string;
  detail: string;
  value: string;
  route: string;
  tone: string;
  permissions: string[];
}

interface MonthlyFinancialPerformanceRow {
  label: string;
  revenue: number;
  expenses: number;
  netProfit: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, HasPermissionDirective],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent {
  readonly session = inject(SessionService);
  readonly roleExperienceService = inject(RoleExperienceService);
  private readonly analyticsService = inject(DashboardAnalyticsService);
  private readonly router = inject(Router);

  loading = true;
  error = '';
  analytics: DashboardAnalytics | null = null;
  financeRange: 'daily' | 'monthly' | 'yearly' = 'daily';
  statRange: 'daily' | 'weekly' | 'monthly' | 'yearly' = 'daily';
  statMetric: 'all' | 'revenue' | 'cost' | 'patients' | 'appointments' | 'admissions' = 'all';
  financeMetric: 'revenue' | 'cost' | 'all' = 'all';
  financeCompare: 'current' | 'goal' | 'both' = 'both';
  filters: DashboardFilters = {
    date_from: this.relativeDate(-29),
    date_to: this.relativeDate(0),
    department: '',
    patient_type: '',
    payment_status: '',
    module_type: '',
  };
  private filterChangeTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.applyRoleDefaultFilters();
    this.loadAnalytics();
  }

  get roleExperience(): RoleExperience {
    return this.roleExperienceService.primaryExperience();
  }

  get roleActions() {
    return this.roleExperienceService.visibleActions(this.roleExperience);
  }

  get roleMetrics(): RoleMetric[] {
    return this.roleExperienceService.visibleMetrics(this.roleExperience).map((metric) => ({
      ...metric,
      value: this.metricValue(metric.label),
    }));
  }

  get showExecutiveAnalytics(): boolean {
    return this.roleExperienceService.canSeeManagementAnalytics();
  }

  get showRoleAnalytics(): boolean {
    return !this.showExecutiveAnalytics && this.roleDashboardCards.length > 0;
  }

  get roleDashboardCards(): RoleDashboardCard[] {
    if (!this.analytics) return [];
    const stockLow = this.analytics.pharmacy_inventory_analytics.low_stock_medicines + this.analytics.pharmacy_inventory_analytics.low_stock_items;
    return [
      {
        label: 'OPD Queue',
        detail: 'Appointments and consultation workload',
        value: String(this.kpiValue("Today's Appointments")),
        route: '/opd/visits',
        tone: 'info',
        permissions: ['opd.view', 'opd.queue.view'],
      },
      {
        label: 'Assigned IPD',
        detail: 'Ward, bed, and admitted patient responsibility',
        value: String(this.kpiValue('Admitted Patients')),
        route: '/ipd/admissions',
        tone: 'warning',
        permissions: ['ipd.view'],
      },
      {
        label: 'Emergency',
        detail: 'ER cases and triage pressure',
        value: String(this.kpiValue('Emergency Cases')),
        route: '/er',
        tone: 'danger',
        permissions: ['er.view', 'er.triage.manage'],
      },
      {
        label: 'Diagnostics',
        detail: 'Lab and radiology work today',
        value: String(this.analytics.lab_radiology_analytics.lab_today + this.analytics.lab_radiology_analytics.radiology_today),
        route: this.session.hasPermission('radiology.view') && !this.session.hasPermission('laboratory.view') ? '/radiology' : '/laboratory',
        tone: 'info',
        permissions: ['laboratory.view', 'radiology.view'],
      },
      {
        label: 'Billing Due',
        detail: 'Invoices pending collection',
        value: this.formatMoney(this.analytics.revenue_analytics.outstanding_due),
        route: '/billing/due-payments',
        tone: 'warning',
        permissions: ['billing.view', 'billing.payment.collect'],
      },
      {
        label: 'Pharmacy',
        detail: 'Sales and dispensing work',
        value: this.formatMoney(this.analytics.pharmacy_inventory_analytics.sales_today),
        route: '/pharmacy',
        tone: 'success',
        permissions: ['pharmacy.view', 'pharmacy.dispense'],
      },
      {
        label: 'Stock Alerts',
        detail: 'Low stock medicines and inventory',
        value: String(stockLow),
        route: '/inventory',
        tone: stockLow ? 'warning' : 'success',
        permissions: ['inventory.view', 'pharmacy.view'],
      },
      {
        label: 'OT Cases',
        detail: 'Operation theatre work queue',
        value: String(this.analytics.ot_analytics.today_surgeries),
        route: '/ot',
        tone: 'info',
        permissions: ['ot.view', 'ot.preop.manage', 'ot.anesthesia.manage'],
      },
      {
        label: 'HR Tasks',
        detail: 'Attendance and leave work',
        value: String(this.analytics.hr_analytics.pending_leave),
        route: '/hr',
        tone: this.analytics.hr_analytics.pending_leave ? 'warning' : 'success',
        permissions: ['hr.view', 'payroll.view', 'hr.self_service'],
      },
    ].filter((card) => this.session.hasAnyPermission(card.permissions));
  }

  get demoJourneySteps(): Array<{ label: string; detail: string; route: string }> {
    return [
      { label: 'Register', detail: 'Patient, doctor, token', route: '/opd/register' },
      { label: 'Collect', detail: 'Invoice and receipt', route: '/billing/create' },
      { label: 'Consult', detail: 'OPD queue and Rx', route: '/opd' },
      { label: 'Admit', detail: 'Bed and advance', route: '/ipd/admit' },
      { label: 'Settle', detail: 'Due payments & billing', route: '/billing/due-payments' },
    ];
  }

  openDemoStep(route: string): void {
    void this.router.navigateByUrl(route);
  }

  openRoute(route: string): void {
    void this.router.navigateByUrl(route);
  }

  get priorityKpis(): DashboardKpi[] {
    const preferred = [
      'Today\'s Appointments',
      "Today's Revenue",
      'Pending Bills',
      'Emergency Cases',
      'Admitted Patients',
      'Lab Tests Today',
      'Low Stock Items',
      'Staff Present',
    ];
    const rows = this.analytics?.kpis || [];
    const picked = preferred
      .map((title) => rows.find((kpi) => kpi.title.trim().toLowerCase() === title.toLowerCase()))
      .filter((kpi): kpi is DashboardKpi => !!kpi);
    const fallback = rows.filter((kpi) => !picked.includes(kpi)).slice(0, Math.max(8 - picked.length, 0));
    return [...picked, ...fallback].slice(0, 8);
  }

  get pendingTaskItems(): Array<{ label: string; detail: string; value: string; route: string; tone: string }> {
    if (!this.analytics) return [];
    const stockLow = this.analytics.pharmacy_inventory_analytics.low_stock_medicines + this.analytics.pharmacy_inventory_analytics.low_stock_items;
    return [
      {
        label: 'Due Collection',
        detail: 'Outstanding billing amount',
        value: this.formatMoney(this.analytics.revenue_analytics.outstanding_due),
        route: '/billing/due-payments',
        tone: 'warning',
      },
      {
        label: 'Diagnostics Queue',
        detail: 'Lab + radiology today',
        value: String(this.analytics.lab_radiology_analytics.lab_today + this.analytics.lab_radiology_analytics.radiology_today),
        route: '/laboratory',
        tone: 'info',
      },
      {
        label: 'Low Stock',
        detail: 'Medicines and inventory items',
        value: String(stockLow),
        route: '/inventory',
        tone: stockLow ? 'warning' : 'good',
      },
      {
        label: 'Pending Leave',
        detail: 'HR approval queue',
        value: String(this.analytics.hr_analytics.pending_leave),
        route: '/hr/leave',
        tone: this.analytics.hr_analytics.pending_leave ? 'warning' : 'good',
      },
    ];
  }

  get dashboardQuickLinks(): Array<{ label: string; detail: string; route: string }> {
    return [
      { label: 'Register OPD', detail: 'New visit and token', route: '/opd/register' },
      { label: 'Create Invoice', detail: 'Billing counter', route: '/billing/create' },
      { label: 'Admit Patient', detail: 'IPD bed workflow', route: '/ipd/admit' },
      { label: 'Dispense Queue', detail: 'Pending prescriptions', route: '/pharmacy/dispense' },
      { label: 'Reports', detail: 'Management summary', route: '/reporting' },
    ];
  }

  financeSeries(kind: 'revenue' | 'cost', which: 'current' | 'goal'): number[] {
    const finance = this.analytics?.finance_line;
    if (!finance) return [];
    const range = finance[this.financeRange];
    const points =
      kind === 'revenue'
        ? which === 'current'
          ? range.revenue_current
          : range.revenue_goal
        : which === 'current'
          ? range.cost_current
          : range.cost_goal;
    return points.map((p) => Number(p.value || 0));
  }

  statChartSeries(): Array<{ key: string; label: string; values: number[]; tone: string }> {
    if (!this.analytics) return [];
    const daily = {
      revenue: this.financeSeries('revenue', 'current'),
      cost: this.financeSeries('cost', 'current'),
      patients: (this.analytics.patient_analytics.daily_visits || []).map((point) => Number(point.value || 0)),
      appointments: (this.analytics.appointment_analytics.trend || []).map((point) => Number(point.value || 0)),
      admissions: (this.analytics.bed_analytics.admission_trend || []).map((point) => Number(point.value || 0)),
    };
    const series = [
      { key: 'revenue', label: 'Revenue', values: this.rangeValues(daily.revenue), tone: 'revenue' },
      { key: 'cost', label: 'Cost', values: this.rangeValues(daily.cost), tone: 'cost' },
      { key: 'patients', label: 'Total Patients', values: this.rangeValues(daily.patients), tone: 'patients' },
      { key: 'appointments', label: 'Appointments', values: this.rangeValues(daily.appointments), tone: 'appointments' },
      { key: 'admissions', label: 'IPD Movement', values: this.rangeValues(daily.admissions), tone: 'admissions' },
    ];
    return this.statMetric === 'all' ? series : series.filter((item) => item.key === this.statMetric);
  }

  statChartMax(): number {
    const values = this.statChartSeries().flatMap((series) => series.values);
    return Math.max(...values, 1);
  }

  statLinePoints(values: number[]): string {
    const max = this.statChartMax();
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 100;
        const y = 100 - (Number(value || 0) / max) * 90;
        return `${x},${y}`;
      })
      .join(' ');
  }

  statSummary(values: number[]): number {
    return values.reduce((sum, value) => sum + Number(value || 0), 0);
  }

  monthlyFinancialPerformanceRows(): MonthlyFinancialPerformanceRow[] {
    const monthly = this.analytics?.finance_line?.monthly;
    if (!monthly) return [];
    const length = Math.max(monthly.revenue_current.length, monthly.cost_current.length);
    return Array.from({ length }).map((_, index) => {
      const revenuePoint = monthly.revenue_current[index];
      const expensePoint = monthly.cost_current[index];
      const revenue = Number(revenuePoint?.value || 0);
      const expenses = Number(expensePoint?.value || 0);
      return {
        label: revenuePoint?.label || expensePoint?.label || revenuePoint?.date || expensePoint?.date || `M${index + 1}`,
        revenue,
        expenses,
        netProfit: revenue - expenses,
      };
    });
  }

  monthlyFinancialMax(): number {
    const values = this.monthlyFinancialPerformanceRows().flatMap((row) => [row.revenue, row.expenses, Math.max(row.netProfit, 0)]);
    return Math.max(...values, 1);
  }

  monthlyFinancialAxisLabels(): number[] {
    const max = this.monthlyFinancialMax();
    return [max, max * 0.75, max * 0.5, max * 0.25, 0];
  }

  monthlyFinancialBarHeight(value: number): number {
    if (value <= 0) return 0;
    return Math.max((value / this.monthlyFinancialMax()) * 100, 3);
  }

  formatCompactMoney(value: number): string {
    const amount = Number(value || 0);
    if (Math.abs(amount) >= 10000000) return `৳${(amount / 10000000).toFixed(1)}Cr`;
    if (Math.abs(amount) >= 100000) return `৳${(amount / 100000).toFixed(1)}L`;
    if (Math.abs(amount) >= 1000) return `৳${(amount / 1000).toFixed(0)}K`;
    return `৳${amount.toFixed(0)}`;
  }

  financeMax(): number {
    const values = [
      ...(this.financeMetric === 'cost' ? [] : this.financeSeries('revenue', 'current')),
      ...(this.financeMetric === 'cost' ? [] : this.financeSeries('revenue', 'goal')),
      ...(this.financeMetric === 'revenue' ? [] : this.financeSeries('cost', 'current')),
      ...(this.financeMetric === 'revenue' ? [] : this.financeSeries('cost', 'goal')),
    ];
    return Math.max(...values, 1);
  }

  financeLinePoints(values: number[]): string {
    const max = this.financeMax();
    const len = values.length;
    if (!len) return '';
    return values
      .map((value, index) => {
        const x = (index / Math.max(len - 1, 1)) * 100;
        const y = 100 - (Number(value || 0) / max) * 90;
        return `${x},${y}`;
      })
      .join(' ');
  }

  financeSummary(kind: 'revenue' | 'cost', which: 'current' | 'goal'): number {
    return this.financeSeries(kind, which).reduce((sum, value) => sum + Number(value || 0), 0);
  }

  kpiByTitle(title: string): DashboardKpi | null {
    const normalized = title.trim().toLowerCase();
    return this.analytics?.kpis.find((kpi) => kpi.title.trim().toLowerCase() === normalized) || null;
  }

  kpiValue(title: string): number {
    return Number(this.kpiByTitle(title)?.value || 0);
  }

  kpiRoute(kpi: DashboardKpi): string {
    const title = kpi.title.toLowerCase();
    if (title.includes('patient')) return '/patients';
    if (title.includes('appointment')) return '/appointments';
    if (title.includes('admitted') || title.includes('discharged') || title.includes('bed')) return '/ipd';
    if (title.includes('emergency')) return '/er';
    if (title.includes('bill')) return '/billing';
    if (title.includes('revenue')) return '/accounting/collections';
    if (title.includes('lab')) return '/laboratory';
    if (title.includes('pharmacy')) return '/pharmacy';
    if (title.includes('ot')) return '/ot';
    if (title.includes('stock')) return '/inventory';
    if (title.includes('staff')) return '/hr/attendance';
    return '/reporting';
  }

  moduleRoute(moduleName: string | null | undefined): string | null {
    const value = (moduleName || '').trim().toLowerCase();
    if (!value) return null;
    if (value.includes('billing') || value.includes('invoice') || value.includes('payment')) return '/billing';
    if (value.includes('account')) return '/accounting';
    if (value.includes('appointment')) return '/appointments';
    if (value.includes('patient')) return '/patients';
    if (value.includes('opd')) return '/opd';
    if (value.includes('ipd') || value.includes('bed') || value.includes('admission')) return '/ipd';
    if (value.includes('er') || value.includes('emergency')) return '/er';
    if (value.includes('lab')) return '/laboratory';
    if (value.includes('radiology')) return '/radiology';
    if (value.includes('pharmacy')) return '/pharmacy';
    if (value.includes('inventory') || value.includes('stock')) return '/inventory';
    if (value.includes('ot') || value.includes('surgery')) return '/ot';
    if (value.includes('hr') || value.includes('payroll') || value.includes('staff')) return '/hr';
    return null;
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

  onFilterChanged(debounce = false): void {
    if (this.filterChangeTimer) {
      clearTimeout(this.filterChangeTimer);
    }

    if (!this.hasValidDateRange()) {
      return;
    }

    if (debounce) {
      this.filterChangeTimer = setTimeout(() => this.loadAnalytics(), 350);
      return;
    }

    this.loadAnalytics();
  }

  private hasValidDateRange(): boolean {
    const from = this.filters.date_from;
    const to = this.filters.date_to;
    if (!from || !to) {
      return true;
    }
    return from <= to;
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

  private rangeValues(values: number[]): number[] {
    if (this.statRange === 'daily') return values;
    if (this.statRange === 'weekly') return this.bucketValues(values, 7);
    if (this.statRange === 'monthly') return this.bucketValues(values, 30);
    return [this.statSummary(values)];
  }

  private bucketValues(values: number[], size: number): number[] {
    const buckets: number[] = [];
    for (let index = 0; index < values.length; index += size) {
      buckets.push(this.statSummary(values.slice(index, index + size)));
    }
    return buckets.length ? buckets : [0];
  }

  private applyRoleDefaultFilters(): void {
    const user = this.session.snapshot.user;
    if (!user) return;
    const roleCodes = new Set(user.roles.map((role) => role.code));
    if (roleCodes.has('DOCTOR')) {
      this.filters.doctor_id = user.id;
      this.filters.patient_type = '';
      return;
    }
    if (roleCodes.has('NURSE')) {
      this.filters.patient_type = 'ipd';
      return;
    }
    if (roleCodes.has('LAB_TECHNICIAN')) {
      this.filters.module_type = 'lab';
      return;
    }
    if (roleCodes.has('RADIOLOGY_TECHNICIAN')) {
      this.filters.module_type = 'radiology';
      return;
    }
    if (roleCodes.has('BILLING_STAFF') || roleCodes.has('ACCOUNTANT')) {
      this.filters.module_type = 'billing';
    }
  }

  private metricValue(label: string): string {
    if (!this.analytics) return '-';
    const normalized = label.toLowerCase();
    if (normalized.includes('appointment') || normalized.includes('check-in')) return String(this.kpiValue("Today's Appointments"));
    if (normalized.includes('patient')) return String(this.kpiValue('Admitted Patients') || this.kpiValue('Total Patients'));
    if (normalized.includes('queue') || normalized.includes('pending') || normalized.includes('opd')) return String(this.kpiValue('Pending Bills') || this.kpiValue("Today's Appointments"));
    if (normalized.includes('emergency')) return String(this.kpiValue('Emergency Cases'));
    if (normalized.includes('revenue')) return this.formatMoney(this.kpiValue("Today's Revenue"));
    if (normalized.includes('bed')) return `${this.analytics.bed_analytics.occupancy_pct}%`;
    if (normalized.includes('stock')) return String(this.analytics.pharmacy_inventory_analytics.low_stock_medicines + this.analytics.pharmacy_inventory_analytics.low_stock_items);
    if (normalized.includes('leave')) return String(this.analytics.hr_analytics.pending_leave);
    if (normalized.includes('attendance')) return `${this.analytics.hr_analytics.attendance_pct}%`;
    if (normalized.includes('alert')) return String(this.analytics.alerts.length);
    return '-';
  }
}
