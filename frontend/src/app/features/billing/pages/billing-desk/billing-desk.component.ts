import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { UiStateService } from '../../../../core/services/ui-state.service';
import {
  BillingInvoice,
  BillingInvoiceFilters,
  BillingInvoiceListItem,
} from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-desk',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './billing-desk.component.html',
  styleUrls: ['./billing-desk.component.scss'],
})
export class BillingDeskComponent {
  private static readonly STATE_KEY = 'ui-state:billing:desk';
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);
  private readonly uiStateService = inject(UiStateService);
  readonly sessionService = inject(SessionService);

  internalReferralDoctors: { id: string; full_name: string }[] = [];
  recentInvoices: BillingInvoiceListItem[] = [];
  latestInvoice: BillingInvoice | null = null;
  collectingPayment = false;
  refunding = false;

  readonly invoiceFilterForm = this.fb.group({
    q: [''],
    internal_referral_user_id: [''],
    status: [''],
    date_from: [''],
    date_to: [''],
  });

  readonly paymentForm = this.fb.group({
    amount: [0, [Validators.required, Validators.min(0.01)]],
    payment_method: ['cash' as const, Validators.required],
    note: [''],
  });

  readonly refundForm = this.fb.group({
    amount: [0, [Validators.required, Validators.min(0.01)]],
    payment_id: [''],
    reason: ['', [Validators.required, Validators.minLength(3)]],
  });

  constructor() {
    this.restoreState();
    this.loadDoctors();
    this.loadInvoices();
    this.route.queryParamMap.subscribe((params) => {
      const invoiceId = params.get('invoiceId');
      if (invoiceId) {
        this.loadInvoiceDetail(invoiceId);
      }
    });
    this.invoiceFilterForm.valueChanges.subscribe(() => this.persistState());
  }

  loadDoctors(): void {
    this.doctorDirectoryService.listDoctors(true).subscribe((doctors) => (this.internalReferralDoctors = doctors));
  }

  loadInvoices(): void {
    this.billingService.listInvoices(this.getInvoiceFilters()).subscribe((invoices) => {
      this.recentInvoices = invoices;
      if (!this.latestInvoice && invoices.length) {
        this.loadInvoiceDetail(invoices[0].id);
      }
    });
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/billing/create' } });
  }

  navigateToCreateInvoice(): void {
    void this.router.navigate(['/billing/create']);
  }

  printInvoice(): void {
    if (!this.latestInvoice) {
      return;
    }

    const invoice = this.latestInvoice;
    const popup = window.open('', '_blank', 'width=900,height=700');
    if (!popup) {
      return;
    }

    popup.document.write(`
      <html>
        <head>
          <title>${invoice.invoice_number}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 32px; color: #102132; }
            h1, h2, h3, p { margin: 0 0 12px; }
            .row { display: flex; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
            .card { border: 1px solid #d9e3ee; border-radius: 12px; padding: 16px; }
            table { width: 100%; border-collapse: collapse; margin-top: 16px; }
            th, td { border-bottom: 1px solid #d9e3ee; padding: 10px; text-align: left; }
            .summary { margin-top: 20px; width: 320px; margin-left: auto; }
            .summary div { display: flex; justify-content: space-between; margin-bottom: 8px; }
          </style>
        </head>
        <body>
          <h1>Billing Invoice</h1>
          <div class="row">
            <div class="card">
              <h3>${invoice.invoice_number}</h3>
              <p>Date: ${new Date(invoice.created_at).toLocaleString()}</p>
              <p>Status: ${this.formatStatus(invoice.status)}</p>
              <p>Payment: ${this.formatStatus(invoice.payment_status)}</p>
              <p>Patient: ${invoice.patient.first_name} ${invoice.patient.last_name}</p>
              <p>Patient No: ${invoice.patient.patient_number}</p>
              <p>Phone: ${invoice.patient.phone ?? '-'}</p>
            </div>
            <div class="card">
              <h3>Referral</h3>
              <p>Doctor: ${invoice.referred_doctor_name ?? '-'}</p>
              <p>Referral Amount: ${this.formatCurrency(invoice.referred_doctor_amount)}</p>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              ${invoice.items
                .map(
                  (item) => `
                    <tr>
                      <td>${item.service_name}</td>
                      <td>${item.quantity}</td>
                      <td>${this.formatCurrency(item.unit_price)}</td>
                      <td>${this.formatCurrency(item.line_total)}</td>
                    </tr>`
                )
                .join('')}
            </tbody>
          </table>
          <div class="summary">
            <div><strong>Sub Total</strong><span>${this.formatCurrency(invoice.sub_total)}</span></div>
            <div><strong>Discount (${invoice.discount_percentage}%)</strong><span>${this.formatCurrency(invoice.discount_amount)}</span></div>
            <div><strong>Total</strong><span>${this.formatCurrency(invoice.total_amount)}</span></div>
            <div><strong>Paid</strong><span>${this.formatCurrency(invoice.paid_amount)}</span></div>
            <div><strong>Due</strong><span>${this.formatCurrency(invoice.due_amount)}</span></div>
            ${invoice.void_reason ? `<div><strong>Void Reason</strong><span>${invoice.void_reason}</span></div>` : ''}
          </div>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  }

  loadInvoiceDetail(invoiceId: string): void {
    this.billingService.getInvoice(invoiceId).subscribe((invoice) => {
      this.latestInvoice = invoice;
      this.syncPaymentForm(invoice);
      this.syncRefundForm(invoice);
      this.notificationService.info(`Loaded invoice ${invoice.invoice_number}.`);
    });
  }

  collectPayment(): void {
    if (!this.latestInvoice || this.latestInvoice.status === 'void' || this.collectingPayment || this.paymentForm.invalid) {
      return;
    }

    this.collectingPayment = true;
    const raw = this.paymentForm.getRawValue();
    this.billingService
      .collectPayment(this.latestInvoice.id, {
        amount: Number(raw.amount ?? 0),
        payment_method: raw.payment_method ?? 'cash',
        note: raw.note?.trim() || null,
      })
      .subscribe({
        next: (invoice) => {
          this.collectingPayment = false;
          this.latestInvoice = invoice;
          this.syncPaymentForm(invoice);
          this.syncRefundForm(invoice);
          this.loadInvoices();
          this.notificationService.success(`Payment collected for ${invoice.invoice_number}.`);
        },
        error: () => {
          this.collectingPayment = false;
        },
      });
  }

  searchInvoices(): void {
    this.persistState();
    this.loadInvoices();
  }

  voidLatestInvoice(): void {
    if (!this.latestInvoice || this.latestInvoice.status === 'void') {
      return;
    }

    const reason = window.prompt('Enter void reason');
    if (!reason?.trim()) {
      return;
    }

    this.billingService.voidInvoice(this.latestInvoice.id, { reason: reason.trim() }).subscribe((invoice) => {
      this.latestInvoice = invoice;
      this.loadInvoices();
      this.persistState();
      this.notificationService.warning(`Invoice ${invoice.invoice_number} voided.`);
    });
  }

  createRefund(): void {
    if (!this.latestInvoice || this.refunding || this.refundForm.invalid || !this.canRefund(this.latestInvoice)) {
      return;
    }

    this.refunding = true;
    const raw = this.refundForm.getRawValue();
    this.billingService
      .createRefund(this.latestInvoice.id, {
        amount: Number(raw.amount ?? 0),
        payment_id: raw.payment_id || null,
        reason: raw.reason?.trim() || '',
      })
      .subscribe({
        next: (invoice) => {
          this.refunding = false;
          this.latestInvoice = invoice;
          this.syncPaymentForm(invoice);
          this.syncRefundForm(invoice);
          this.loadInvoices();
          this.notificationService.warning(`Refund posted for ${invoice.invoice_number}.`);
        },
        error: () => {
          this.refunding = false;
        },
      });
  }

  formatStatus(status: string): string {
    return status.replace('_', ' ').toUpperCase();
  }

  canCollectPayment(invoice: BillingInvoice): boolean {
    return invoice.status !== 'void' && invoice.payment_status !== 'paid' && Number(invoice.due_amount) > 0;
  }

  canRefund(invoice: BillingInvoice): boolean {
    return invoice.status !== 'void' && Number(invoice.paid_amount) > 0;
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  private getInvoiceFilters(): BillingInvoiceFilters {
    const raw = this.invoiceFilterForm.getRawValue();
    return {
      q: raw.q?.trim() || undefined,
      internal_referral_user_id: raw.internal_referral_user_id || undefined,
      status: raw.status || undefined,
      date_from: raw.date_from || undefined,
      date_to: raw.date_to || undefined,
    };
  }

  private restoreState(): void {
    const state = this.uiStateService.load<{ filters?: BillingInvoiceFilters }>(BillingDeskComponent.STATE_KEY);
    if (!state?.filters) {
      return;
    }

    this.invoiceFilterForm.patchValue({
      q: state.filters.q ?? '',
      internal_referral_user_id: state.filters.internal_referral_user_id ?? '',
      status: state.filters.status ?? '',
      date_from: state.filters.date_from ?? '',
      date_to: state.filters.date_to ?? '',
    });
  }

  private persistState(): void {
    this.uiStateService.save(BillingDeskComponent.STATE_KEY, {
      filters: this.getInvoiceFilters(),
    });
  }

  private syncPaymentForm(invoice: BillingInvoice): void {
    this.paymentForm.patchValue({
      amount: Number(invoice.due_amount),
      payment_method: 'cash',
      note: '',
    });
  }

  private syncRefundForm(invoice: BillingInvoice): void {
    this.refundForm.patchValue({
      amount: Number(invoice.paid_amount),
      payment_id: '',
      reason: '',
    });
  }
}
