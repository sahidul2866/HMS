import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { BillingReferralSummary, BillingSummary } from '../../../billing/models/billing.models';
import { BillingServiceApi } from '../../../billing/services/billing.service';
import { ClinicalOperationsSummary, ReportCatalog, ReportCatalogItem } from '../../models/reporting.models';
import { ReportingServiceApi } from '../../services/reporting.service';

type ReportMode = 'data' | 'chart';
type ReportMetric = { label: string; value: string | number; raw: number; note: string };
type ReportingPage = 'library' | 'finance' | 'clinical' | 'referrals';

@Component({
  selector: 'app-reporting-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './reporting-overview.component.html',
  styleUrls: ['./reporting-overview.component.scss'],
})
export class ReportingOverviewComponent {
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly reportingService = inject(ReportingServiceApi);
  private readonly route = inject(ActivatedRoute);

  summary: BillingSummary | null = null;
  referralSummary: BillingReferralSummary[] = [];
  clinicalSummary: ClinicalOperationsSummary | null = null;
  catalog: ReportCatalog | null = null;
  selectedCategory = 'Accounting & Finance';
  selectedReport: ReportCatalogItem | null = null;
  categoryLocked = false;
  reportMode: ReportMode = 'data';
  reportingPage: ReportingPage = 'library';

  readonly form = this.fb.group({
    date_from: [''],
    date_to: [''],
  });

  constructor() {
    this.route.data.subscribe((data) => {
      this.reportingPage = (data['reportingPage'] as ReportingPage | undefined) || 'library';
      this.categoryLocked = false;
      this.selectedCategory = 'Management Summary';
      this.loadReports();
    });
    this.form.valueChanges.subscribe(() => {
      if (this.hasValidDateRange()) {
        this.loadReports();
      }
    });
  }

  get pageTitle(): string {
    if (this.reportingPage === 'finance') return 'Financial Summary';
    if (this.reportingPage === 'clinical') return 'Clinical Operations';
    if (this.reportingPage === 'referrals') return 'Doctor Referral Summary';
    return 'Report Library';
  }

  get pageSubtitle(): string {
    if (this.reportingPage === 'finance') return 'Revenue, discounts, posted invoices, and finance-facing totals.';
    if (this.reportingPage === 'clinical') return 'Operational movement across appointments, OPD, IPD, diagnostics, billing, and pharmacy.';
    if (this.reportingPage === 'referrals') return 'Referral doctor contribution, net billing, and payout exposure.';
    return 'Choose a report from the library, then review insights in data or chart view.';
  }

  get showLibrary(): boolean {
    return this.reportingPage === 'library';
  }

  get showFinance(): boolean {
    return this.reportingPage === 'finance';
  }

  get showClinical(): boolean {
    return this.reportingPage === 'clinical';
  }

  get showReferrals(): boolean {
    return this.reportingPage === 'referrals';
  }

  loadReports(): void {
    const filters = {
      date_from: this.form.getRawValue().date_from || undefined,
      date_to: this.form.getRawValue().date_to || undefined,
    };
    this.billingService.getSummary(filters).subscribe((summary) => (this.summary = summary));
    this.billingService.getReferralSummary(filters).subscribe((summary) => (this.referralSummary = summary));
    this.reportingService.getClinicalSummary().subscribe((summary) => (this.clinicalSummary = summary));
    this.reportingService.getCatalog().subscribe((catalog) => {
      this.catalog = catalog;
      if (!catalog.categories.includes(this.selectedCategory)) {
        this.selectedCategory = catalog.categories[0] || '';
      }
      this.selectedReport = this.filteredReports[0] || null;
    });
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  get clinicalWorkflowRows(): Array<{ workflow: string; pending: number; active: number; verified: number | string }> {
    if (!this.clinicalSummary) {
      return [];
    }
    return [
      {
        workflow: 'Appointments',
        pending: this.clinicalSummary.scheduled_appointments,
        active: this.clinicalSummary.completed_appointments,
        verified: this.clinicalSummary.cancelled_appointments,
      },
      {
        workflow: 'Laboratory',
        pending: this.clinicalSummary.pending_laboratory,
        active: this.clinicalSummary.completed_laboratory,
        verified: this.clinicalSummary.verified_laboratory,
      },
      {
        workflow: 'Radiology',
        pending: this.clinicalSummary.pending_radiology,
        active: this.clinicalSummary.completed_radiology,
        verified: this.clinicalSummary.verified_radiology,
      },
      {
        workflow: 'Billing',
        pending: this.clinicalSummary.unpaid_invoices + this.clinicalSummary.partial_invoices,
        active: this.clinicalSummary.paid_invoices,
        verified: '-',
      },
    ];
  }

  get filteredReports(): ReportCatalogItem[] {
    return (this.catalog?.reports || []).filter((item) => item.category === this.selectedCategory);
  }

  onCategoryChange(category: string): void {
    this.selectedCategory = category;
    this.selectedReport = this.filteredReports[0] || null;
  }

  selectReport(report: ReportCatalogItem): void {
    this.selectedReport = report;
    this.reportMode = 'data';
  }

  setReportMode(mode: ReportMode): void {
    this.reportMode = mode;
  }

  selectedReportMetrics(): ReportMetric[] {
    if (!this.selectedReport) {
      return [];
    }
    switch (this.selectedReport.category) {
      case 'Accounting & Finance':
        return [
          this.metric('Gross Amount', Number(this.summary?.gross_amount || 0), true, 'Total billed value before discount.'),
          this.metric('Net Revenue', Number(this.summary?.net_amount || 0), true, 'Revenue after discounts.'),
          this.metric('Posted Invoices', this.summary?.posted_invoice_count || 0, false, 'Finalized billing volume.'),
          this.metric('Outstanding Due', Number(this.clinicalSummary?.outstanding_due_amount || 0), true, 'Uncollected patient balance.'),
        ];
      case 'Patient':
        return [
          this.metric('OPD Visits', this.clinicalSummary?.opd_visits || 0, false, 'Outpatient workload.'),
          this.metric('Billed OPD', this.clinicalSummary?.opd_billed_visits || 0, false, 'Visits connected to billing.'),
          this.metric('Completed OPD', this.clinicalSummary?.opd_completed_visits || 0, false, 'Visits closed clinically.'),
          this.metric('Active IPD', this.clinicalSummary?.ipd_active_admissions || 0, false, 'Currently admitted patients.'),
        ];
      case 'Appointment':
        return [
          this.metric('Scheduled', this.clinicalSummary?.scheduled_appointments || 0, false, 'Booked appointment count.'),
          this.metric('Completed', this.clinicalSummary?.completed_appointments || 0, false, 'Finished appointment count.'),
          this.metric('Cancelled', this.clinicalSummary?.cancelled_appointments || 0, false, 'Cancelled appointment count.'),
          this.metric('Completion Rate', this.percentValue(this.clinicalSummary?.completed_appointments || 0, this.clinicalSummary?.scheduled_appointments || 0), false, 'Completed appointments as a percentage of scheduled appointments.', '%'),
        ];
      case 'Admission & Bed':
        return [
          this.metric('Active IPD', this.clinicalSummary?.ipd_active_admissions || 0, false, 'Current inpatient load.'),
          this.metric('Total Admissions', this.clinicalSummary?.ipd_total_admissions || 0, false, 'Admission volume.'),
          this.metric('Discharged', this.clinicalSummary?.ipd_discharged_admissions || 0, false, 'Discharged patient count.'),
          this.metric('Discharge Rate', this.percentValue(this.clinicalSummary?.ipd_discharged_admissions || 0, this.clinicalSummary?.ipd_total_admissions || 0), false, 'Discharges as a percentage of total admissions.', '%'),
        ];
      case 'Lab & Radiology':
        return [
          this.metric('Pending Lab', this.clinicalSummary?.pending_laboratory || 0, false, 'Lab orders waiting for completion or verification.'),
          this.metric('Verified Lab', this.clinicalSummary?.verified_laboratory || 0, false, 'Lab results ready for clinical use.'),
          this.metric('Pending Radiology', this.clinicalSummary?.pending_radiology || 0, false, 'Imaging orders waiting for completion or verification.'),
          this.metric('Verified Radiology', this.clinicalSummary?.verified_radiology || 0, false, 'Radiology reports ready for release.'),
        ];
      case 'Pharmacy':
        return [
          this.metric('Pending Prescriptions', this.clinicalSummary?.pending_prescriptions || 0, false, 'Prescriptions still needing pharmacy action.'),
          this.metric('Dispenses', this.clinicalSummary?.pharmacy_dispenses || 0, false, 'Dispensed prescription volume.'),
          this.metric('Collected Amount', Number(this.clinicalSummary?.collected_amount || 0), true, 'Collected amount tied to patient workflows.'),
          this.metric('Refunded Amount', Number(this.clinicalSummary?.refunded_amount || 0), true, 'Refunded amount requiring review.'),
        ];
      default:
        return [
          this.metric('OPD Visits', this.clinicalSummary?.opd_visits || 0, false, 'Outpatient demand signal.'),
          this.metric('Active IPD', this.clinicalSummary?.ipd_active_admissions || 0, false, 'Current inpatient pressure.'),
          this.metric('Net Revenue', Number(this.summary?.net_amount || 0), true, 'Revenue after discounts.'),
          this.metric('Outstanding Due', Number(this.clinicalSummary?.outstanding_due_amount || 0), true, 'Uncollected patient balance.'),
        ];
    }
  }

  reportInsights(): string[] {
    const metrics = this.selectedReportMetrics();
    const highest = [...metrics].sort((left, right) => right.raw - left.raw)[0];
    const alerts = metrics.filter((metric) => /Pending|Outstanding|Refunded|Cancelled|Void|Due/i.test(metric.label) && metric.raw > 0);
    const insights = [
      highest ? `${highest.label} is the strongest signal in this report at ${highest.value}.` : 'No report data is available yet for the selected filters.',
    ];
    if (alerts.length) {
      insights.push(`${alerts[0].label} needs attention: ${alerts[0].value}.`);
    }
    if (this.selectedReport?.category === 'Accounting & Finance' && this.summary) {
      insights.push(`Discount impact is ${this.formatCurrency(this.summary.discount_amount)} against ${this.formatCurrency(this.summary.gross_amount)} gross billing.`);
    } else if (this.selectedReport?.category === 'Appointment') {
      insights.push(`Appointment completion is ${this.percent(this.clinicalSummary?.completed_appointments || 0, this.clinicalSummary?.scheduled_appointments || 0)}.`);
    } else if (this.selectedReport?.category === 'Lab & Radiology') {
      insights.push(`Combined pending diagnostics: ${(this.clinicalSummary?.pending_laboratory || 0) + (this.clinicalSummary?.pending_radiology || 0)} order(s).`);
    }
    return insights.slice(0, 3);
  }

  chartWidth(metric: ReportMetric): number {
    const max = Math.max(...this.selectedReportMetrics().map((item) => item.raw), 1);
    return Math.max(4, Math.round((metric.raw / max) * 100));
  }

  printSelectedReport(): void {
    window.print();
  }

  exportSelectedReport(): void {
    if (!this.selectedReport) {
      return;
    }
    const rows = [
      ['Report', this.selectedReport.name],
      ['Category', this.selectedReport.category],
      ['Date From', this.form.getRawValue().date_from || 'All'],
      ['Date To', this.form.getRawValue().date_to || 'All'],
      ...this.selectedReportMetrics().map((metric) => [metric.label, String(metric.value)]),
    ];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${this.selectedReport.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  private hasValidDateRange(): boolean {
    const { date_from, date_to } = this.form.getRawValue();
    if (!date_from || !date_to) return true;
    return date_from <= date_to;
  }

  private percent(value: number, total: number): string {
    if (!total) {
      return '0%';
    }
    return `${Math.round((value / total) * 100)}%`;
  }

  private percentValue(value: number, total: number): number {
    if (!total) {
      return 0;
    }
    return Math.round((value / total) * 100);
  }

  private metric(label: string, raw: number, currency: boolean, note: string, suffix = ''): ReportMetric {
    return {
      label,
      raw,
      value: currency ? this.formatCurrency(raw) : `${raw}${suffix}`,
      note,
    };
  }
}
