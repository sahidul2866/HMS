import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { FloatingAssistantComponent } from '../../../../shared/components/floating-assistant/floating-assistant.component';
import { BillingInvoiceListItem, BillingReferralSummary, BillingSummary } from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-overview',
  standalone: true,
  imports: [CommonModule, FloatingAssistantComponent],
  templateUrl: './billing-overview.component.html',
  styleUrls: ['./billing-overview.component.scss'],
})
export class BillingOverviewComponent {
  private readonly billingService = inject(BillingServiceApi);
  private readonly router = inject(Router);

  summary: BillingSummary | null = null;
  referrals: BillingReferralSummary[] = [];
  recentInvoices: BillingInvoiceListItem[] = [];
  dueInvoices: BillingInvoiceListItem[] = [];

  readonly assistantQuickActions = [
    'Show pending payments',
    'Search invoice by patient ID',
    'Show today’s collection',
    'Show revenue analysis',
    'Show due invoices',
    'Show hospital summary',
    'Check invoice status',
    'How much collected today?',
  ];

  constructor() {
    this.load();
  }

  load(): void {
    this.billingService.getSummary().subscribe((summary) => (this.summary = summary));
    this.billingService.getReferralSummary().subscribe((items) => (this.referrals = items.slice(0, 5)));
    this.billingService.listInvoices({ status: 'posted' }).subscribe((items) => {
      this.recentInvoices = items.slice(0, 8);
      this.dueInvoices = items.filter((item) => Number(item.due_amount || 0) > 0).slice(0, 6);
    });
  }

  goToInvoiceList(): void {
    void this.router.navigate(['/billing/list']);
  }

  goToDueList(): void {
    void this.router.navigate(['/billing/due-payments']);
  }

  goToCreateInvoice(): void {
    void this.router.navigate(['/billing/create']);
  }

  openInvoice(invoiceId: string): void {
    void this.router.navigate(['/billing/list'], { queryParams: { invoiceId } });
  }

  get revenueCards(): Array<{ label: string; value: string; detail: string }> {
    if (!this.summary) return [];
    return [
      { label: 'Net Collection', value: this.formatCurrency(this.summary.net_amount), detail: `${this.summary.posted_invoice_count} posted invoices` },
      { label: 'Outstanding Due', value: this.formatCurrency(this.dueQueueTotal), detail: `${this.dueInvoices.length} invoices need follow-up` },
      { label: 'Discounts', value: this.formatCurrency(this.summary.discount_amount), detail: `${this.discountRate}% of gross` },
      { label: 'Referral Exposure', value: this.formatCurrency(this.summary.referred_doctor_amount), detail: 'Doctor payout review' },
    ];
  }

  get dueQueueTotal(): number {
    return this.dueInvoices.reduce((sum, invoice) => sum + Number(invoice.due_amount || 0), 0);
  }

  get discountRate(): number {
    const gross = Number(this.summary?.gross_amount || 0);
    return gross ? Math.round((Number(this.summary?.discount_amount || 0) / gross) * 100) : 0;
  }

  get collectionRate(): number {
    const net = Number(this.summary?.net_amount || 0);
    const due = this.dueQueueTotal;
    return net + due ? Math.round((net / (net + due)) * 100) : 100;
  }

  formatCurrency(value: string | number | null | undefined): string {
    return `BDT ${Number(value || 0).toFixed(2)}`;
  }
}
