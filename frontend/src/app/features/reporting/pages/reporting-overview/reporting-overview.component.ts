import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { BillingReferralSummary, BillingSummary } from '../../../billing/models/billing.models';
import { BillingServiceApi } from '../../../billing/services/billing.service';

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

  summary: BillingSummary | null = null;
  referralSummary: BillingReferralSummary[] = [];

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
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }
}
