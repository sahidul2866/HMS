import { SessionService } from '../../../../core/services/session.service';
import { CommonModule } from '@angular/common';
import { Component, inject, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { DialogDirective } from '../../../../shared/directives/dialog.directive';
import { Router } from '@angular/router';

import { FloatingAssistantComponent } from '../../../../shared/components/floating-assistant/floating-assistant.component';
import { BillingInvoiceListItem, BillingReferralSummary, BillingSummary } from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogDirective, FloatingAssistantComponent],
  templateUrl: './billing-overview.component.html',
  styleUrls: ['./billing-overview.component.scss'],
})
export class BillingOverviewComponent implements OnDestroy {
  readonly access = inject(SessionService);
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
    if(this.access.hasPermission('reporting.financial.view')) this.billingService.getSummary().subscribe((summary) => (this.summary = summary));
    if(this.access.hasPermission('reporting.financial.view')) this.billingService.getReferralSummary({ limit: 5, doctors_only: true }).subscribe((items) => (this.referrals = [...items].sort((a, b) => Number(b.net_amount) - Number(a.net_amount)).slice(0, 5)));
    this.billingService.listInvoices({ status: 'posted' }).subscribe((items) => {
      this.recentInvoices = items.slice(0, 8);
      this.dueInvoices = items.filter((item) => Number(item.due_amount || 0) > 0);
    });
  }

  referralDialog = false;
  referralSearch = '';
  referralPage = 0;
  referralRows: BillingReferralSummary[] = [];
  selectedReferral: BillingReferralSummary | null = null;
  referralBills: BillingInvoiceListItem[] = [];
  referralLoading = false;
  referralError = '';
  referralHasNext = false;
  private referralRequest?: Subscription;
  readonly referralPageSize = 20;

  ngOnDestroy(): void { this.referralRequest?.unsubscribe(); }

  showReferralDoctors(): void {
    this.referralDialog = true;
    this.selectedReferral = null;
    this.referralPage = 0;
    this.loadReferralPage();
  }

  showReferralBills(row: BillingReferralSummary): void {
    this.referralDialog = true;
    this.selectedReferral = row;
    this.referralPage = 0;
    this.loadReferralPage();
  }

  searchReferrals(): void {
    this.referralPage = 0;
    this.loadReferralPage();
  }

  changeReferralPage(delta: number): void {
    this.referralPage += delta;
    this.loadReferralPage();
  }

  closeReferralDialog(): void {
    this.referralRequest?.unsubscribe();
    this.referralDialog = false;
  }

  loadReferralPage(): void {
    this.referralRequest?.unsubscribe();
    this.referralLoading = true;
    this.referralError = '';
    this.referralRows = [];
    this.referralBills = [];
    this.referralHasNext = false;
    const paging = { limit: this.referralPageSize + 1, offset: this.referralPage * this.referralPageSize };
    const fail = () => { this.referralLoading = false; this.referralError = 'Could not load referral records. Please retry.'; };
    if (this.selectedReferral) {
      const row = this.selectedReferral;
      this.referralRequest = this.billingService.listInvoices({ ...paging, status: 'posted',
        internal_referral_user_id: row.internal_referral_user_id || undefined,
        referral_name: row.internal_referral_user_id ? undefined : row.referred_doctor_name,
      }).subscribe({ next: items => {
        this.referralBills = items.slice(0, this.referralPageSize);
        this.referralHasNext = items.length > this.referralPageSize;
        this.referralLoading = false;
      }, error: fail });
    } else {
      this.referralRequest = this.billingService.getReferralSummary({ ...paging, q: this.referralSearch.trim(), doctors_only: true }).subscribe({ next: items => {
        this.referralRows = items.slice(0, this.referralPageSize);
        this.referralHasNext = items.length > this.referralPageSize;
        this.referralLoading = false;
      }, error: fail });
    }
  }

  goToInvoiceList(): void {
    void this.router.navigate(['/billing/list']);
  }

  goToDueList(showAll = false): void {
    void this.router.navigate(['/billing/due-payments'], { queryParams: showAll ? { view: 'all-pending' } : {} });
  }

  goToCreateInvoice(): void {
    void this.router.navigate(['/billing/create']);
  }

  openInvoice(invoiceId: string): void {
    this.closeReferralDialog();
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
