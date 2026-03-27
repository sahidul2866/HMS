import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { BillingReferralSummary, BillingSummary } from '../../../billing/models/billing.models';
import { BillingServiceApi } from '../../../billing/services/billing.service';
import { ClinicalOperationsSummary } from '../../models/reporting.models';
import { ReportingServiceApi } from '../../services/reporting.service';

@Component({
  selector: 'app-reporting-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './reporting-overview.component.html',
  styleUrls: ['./reporting-overview.component.scss'],
})
export class ReportingOverviewComponent {
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly reportingService = inject(ReportingServiceApi);

  summary: BillingSummary | null = null;
  referralSummary: BillingReferralSummary[] = [];
  clinicalSummary: ClinicalOperationsSummary | null = null;

  readonly form = this.fb.group({
    date_from: [''],
    date_to: [''],
  });

  constructor() {
    this.loadReports();
  }

  loadReports(): void {
    const filters = {
      date_from: this.form.getRawValue().date_from || undefined,
      date_to: this.form.getRawValue().date_to || undefined,
    };
    this.billingService.getSummary(filters).subscribe((summary) => (this.summary = summary));
    this.billingService.getReferralSummary(filters).subscribe((summary) => (this.referralSummary = summary));
    this.reportingService.getClinicalSummary().subscribe((summary) => (this.clinicalSummary = summary));
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
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
}
