import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { UiStateService } from '../../../../core/services/ui-state.service';
import { buildBarcodeSvg, escapePrintHtml } from '../../../../shared/utils/print-layout.utils';
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
  private readonly sanitizer = inject(DomSanitizer);
  private readonly notificationService = inject(NotificationService);
  private readonly uiStateService = inject(UiStateService);
  readonly sessionService = inject(SessionService);

  internalReferralDoctors: { id: string; full_name: string }[] = [];
  recentInvoices: BillingInvoiceListItem[] = [];
  latestInvoice: BillingInvoice | null = null;
  invoicePreviewInvoice: BillingInvoice | null = null;
  invoicePreviewHtml: string | null = null;
  invoicePreviewUrl: SafeResourceUrl | null = null;
  collectingPayment = false;
  refunding = false;
  viewMode: 'all' | 'due' = 'all';
  private invoicePreviewObjectUrl: string | null = null;

  @ViewChild('invoiceFrame') invoiceFrame?: ElementRef<HTMLIFrameElement>;

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
    this.route.data.subscribe((data) => {
      this.viewMode = data['billingView'] === 'due' ? 'due' : 'all';
      this.loadInvoices();
    });
    this.route.queryParamMap.subscribe((params) => {
      const invoiceId = params.get('invoiceId');
      const shouldPrint = params.get('printInvoice') === '1';
      if (invoiceId) {
        this.loadInvoiceDetail(invoiceId, shouldPrint);
      }
    });
    this.invoiceFilterForm.valueChanges.subscribe(() => this.persistState());
  }

  loadDoctors(): void {
    this.doctorDirectoryService.listDoctors(true).subscribe((doctors) => (this.internalReferralDoctors = doctors));
  }

  loadInvoices(): void {
    this.billingService.listInvoices(this.getInvoiceFilters()).subscribe((invoices) => {
      this.recentInvoices = this.viewMode === 'due' ? invoices.filter((invoice) => this.isDueInvoice(invoice)) : invoices;
      if (this.latestInvoice && !this.recentInvoices.find((invoice) => invoice.id === this.latestInvoice?.id)) {
        this.latestInvoice = null;
      }
      if (!this.latestInvoice && this.recentInvoices.length) {
        this.loadInvoiceDetail(this.recentInvoices[0].id);
      }
    });
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/billing/create' } });
  }

  navigateToCreateInvoice(): void {
    void this.router.navigate(['/billing/create']);
  }

  get pageTitle(): string {
    return this.viewMode === 'due' ? 'Due Payment List' : 'Billing List';
  }

  get pageSubtitle(): string {
    return this.viewMode === 'due'
      ? 'Work the unpaid and partially paid invoice queue, collect dues, and keep outstanding balances under control.'
      : 'Review posted invoices, inspect billing detail, print invoices, and trace payment activity from one searchable list.';
  }

  get queueLabel(): string {
    return this.viewMode === 'due' ? 'Due Queue' : 'Invoice Queue';
  }

  get detailTitle(): string {
    return this.viewMode === 'due' ? 'Due Payment Detail' : 'Invoice Detail';
  }

  get listTitle(): string {
    return this.viewMode === 'due' ? 'Due Payment List' : 'Billing List';
  }

  get listCopy(): string {
    return this.viewMode === 'due'
      ? 'This queue shows only posted invoices with outstanding due amount so the desk can collect balance quickly.'
      : 'Filter the billing stream, inspect older invoices, and jump back into print-ready invoice details.';
  }

  get isDueMode(): boolean {
    return this.viewMode === 'due';
  }

  get billingKpis(): Array<{ label: string; value: string; tone: string }> {
    const invoices = this.recentInvoices;
    const total = invoices.reduce((sum, invoice) => sum + Number(invoice.total_amount || 0), 0);
    const paid = invoices.reduce((sum, invoice) => sum + Number(invoice.paid_amount || 0), 0);
    const due = invoices.reduce((sum, invoice) => sum + Number(invoice.due_amount || 0), 0);
    const refunded = invoices.reduce((sum, invoice) => sum + Number(invoice.refunded_amount || 0), 0);
    const discounts = invoices.reduce((sum, invoice) => {
      const fullInvoice = invoice as BillingInvoice;
      const itemDiscount = Number(fullInvoice.item_discount_amount || 0);
      const invoiceDiscount = Number(fullInvoice.invoice_discount_amount || 0);
      return sum + itemDiscount + invoiceDiscount;
    }, 0);
    const pending = invoices.filter((invoice) => Number(invoice.due_amount || 0) > 0).length;
    return [
      { label: 'Collection', value: this.formatCurrency(paid), tone: 'good' },
      { label: 'Invoice Value', value: this.formatCurrency(total), tone: 'info' },
      { label: 'Pending Bills', value: String(pending), tone: pending ? 'warn' : 'good' },
      { label: 'Due Amount', value: this.formatCurrency(due), tone: due ? 'danger' : 'good' },
      { label: 'Refunded', value: this.formatCurrency(refunded), tone: refunded ? 'warn' : 'info' },
      { label: 'Discounts', value: this.formatCurrency(discounts), tone: discounts ? 'warn' : 'info' },
    ];
  }

  get paymentMethodSummary(): Array<{ label: string; value: string }> {
    const map = new Map<string, number>();
    for (const payment of this.latestInvoice?.payments || []) {
      map.set(payment.payment_method, (map.get(payment.payment_method) || 0) + Number(payment.amount || 0));
    }
    return [...map.entries()].map(([label, value]) => ({ label: this.formatStatus(label), value: this.formatCurrency(value) }));
  }

  printInvoice(): void {
    if (!this.latestInvoice) {
      return;
    }
    this.openInvoicePreview(this.latestInvoice);
  }

  private buildInvoicePrintHtml(invoice: BillingInvoice): string {
    const patientName = `${invoice.patient.first_name} ${invoice.patient.last_name}`.trim();
    const combinedBarcode = buildBarcodeSvg(`${invoice.patient.patient_number} | ${invoice.invoice_number}`, 'Patient + Invoice ID');
    const printTime = new Date().toLocaleString();
    const patientAge = this.getPatientAgeLabel(invoice.patient.date_of_birth);
    const itemDiscountAmount = Number(invoice.item_discount_amount ?? 0);
    const invoiceDiscountAmount = Number(invoice.invoice_discount_amount ?? 0);
    const grossAmount = Number(invoice.sub_total ?? 0) + itemDiscountAmount;
    const dueAmount = Number(invoice.due_amount ?? 0);
    const paidAmount = Number(invoice.paid_amount ?? 0);
    const preparedBy = this.sessionService.snapshot.user?.full_name || 'Billing Desk';
    const rows = invoice.items
      .map(
        (item, index) => `
          <tr>
            <td>${index + 1}</td>
            <td>${escapePrintHtml(item.service_name)}</td>
            <td>${this.formatCurrency(item.unit_price)}</td>
            <td>${escapePrintHtml(item.discount_percentage)}</td>
            <td>${this.formatCurrency(item.line_total)}</td>
          </tr>`
      )
      .join('');
    const summaryDiscountRows = `
      ${itemDiscountAmount > 0 ? `<tr><td colspan="4" style="text-align:right;"><b>Item Discount</b></td><td>${this.formatCurrency(itemDiscountAmount)}</td></tr>` : ''}
      ${invoiceDiscountAmount > 0 ? `<tr><td colspan="4" style="text-align:right;"><b>Extra Discount</b></td><td>${this.formatCurrency(invoiceDiscountAmount)}</td></tr>` : ''}
    `;
    const renderCopy = (copyLabel: string) => `
      <section class="invoice-copy">
        <div class="copy-header">
          <div class="brand-block">
            <div class="brand-mark">MP</div>
            <div class="brand-copy">
              <p class="clinic-name">MediProfit</p>
              <p>Address : 461, Firmview Super Market, Firmgate, Dhaka-1205</p>
              <p>Contact : +8801720981682</p>
            </div>
          </div>
          <div class="copy-tag">${escapePrintHtml(copyLabel)}</div>
        </div>

        <div class="title-band"><strong>Invoice</strong></div>

        <div class="detail-grid">
          <section class="info-card">
            <label><u>Patient Information</u></label>
            <div class="meta-list">
              <div><span>Patient ID</span><strong>${escapePrintHtml(invoice.patient.patient_number)}</strong></div>
              <div><span>Name</span><strong>${escapePrintHtml(patientName)}</strong></div>
              <div><span>Mobile</span><strong>${escapePrintHtml(invoice.patient.phone ?? '-')}</strong></div>
              <div><span>Age</span><strong>${escapePrintHtml(patientAge)}</strong></div>
            </div>
          </section>

          <section class="barcode-card">
            ${combinedBarcode}
            <div class="meta-list compact-list">
              <div><span>ID No.</span><strong>${escapePrintHtml(invoice.invoice_number)}</strong></div>
              <div><span>Print Time</span><strong>${escapePrintHtml(printTime)}</strong></div>
              <div><span>Consultant</span><strong>${escapePrintHtml(invoice.referred_doctor_name || '-')}</strong></div>
            </div>
          </section>
        </div>

        <section class="table-card">
          <table>
            <thead>
              <tr>
                <th>SL</th>
                <th>Service</th>
                <th>Rate</th>
                <th>Discount (%)</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
              <tr>
                <td colspan="4" style="text-align:right;"><b>Total Amount</b></td>
                <td>${this.formatCurrency(grossAmount)}</td>
              </tr>
              ${summaryDiscountRows}
              <tr>
                <td colspan="4" style="text-align:right;"><b>Payment Amount</b></td>
                <td>${this.formatCurrency(paidAmount)}</td>
              </tr>
              <tr>
                <td colspan="4" style="text-align:right;"><b>Due Amount</b></td>
                <td>${this.formatCurrency(dueAmount)}</td>
              </tr>
              <tr>
                <td colspan="5"><b>Inward :</b> ${escapePrintHtml(this.amountInWords(paidAmount || Number(invoice.total_amount ?? 0)))} Only.</td>
              </tr>
            </tbody>
          </table>
        </section>

        <div class="footer-row">
          <div class="stamp-wrap">
            ${dueAmount > 0 ? '<div class="due-stamp">Due</div>' : '<div class="paid-stamp">Paid</div>'}
          </div>
          <div class="prepared-by">
            <p><b>Prepared by</b></p>
            <p>${escapePrintHtml(preparedBy)}</p>
            <p>Billing Desk</p>
          </div>
        </div>
      </section>
    `;

    return `
      <!DOCTYPE html>
      <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>${escapePrintHtml(invoice.invoice_number)}</title>
          <style>
            :root { --ink:#17304a; --muted:#65758a; --line:#d7dee7; --panel:#f6f8fb; --brand:#0d5c63; --brand-deep:#123b56; }
            * { box-sizing:border-box; }
            body { font-family: Arial, sans-serif; margin: 0; padding: 18px; color: var(--ink); background: #eff4f8; }
            h1, h2, h3, p { margin: 0; }
            .preview-shell { max-width: 1020px; margin: 0 auto; display: grid; gap: 20px; }
            .invoice-copy { display:grid; gap:16px; padding: 24px 26px 28px; background:white; border:1px solid var(--line); border-radius: 24px; box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08); }
            .copy-header, .footer-row { display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; align-items:flex-start; }
            .brand-block { display:flex; gap:14px; align-items:center; }
            .brand-mark { width:72px; height:72px; border-radius:18px; display:grid; place-items:center; background:linear-gradient(135deg, var(--brand-deep), var(--brand)); color:white; font-size:24px; font-weight:800; letter-spacing:.08em; }
            .brand-copy { display:grid; gap:4px; }
            .clinic-name { font-size:23px; font-weight:800; }
            .copy-tag { padding:10px 14px; border-radius:999px; border:1px solid var(--line); background:#f8fafc; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.1em; }
            .title-band { padding: 12px 16px; text-align:center; border:1px solid var(--line); border-radius:18px; background:linear-gradient(180deg, #f7fafc, #eef4f8); font-size:30px; }
            .detail-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:16px; }
            .barcode-card, .info-card, .table-card { padding:16px; border:1px solid var(--line); border-radius:18px; background:var(--panel); }
            .id-barcode-svg { width:100%; height:92px; display:block; }
            .meta-list { display:grid; gap:10px; margin-top: 10px; }
            .meta-list div { display:flex; justify-content:space-between; gap:12px; padding-bottom:8px; border-bottom:1px dashed #ccd7e2; }
            .meta-list div:last-child { border-bottom:0; padding-bottom:0; }
            .meta-list span { color: var(--muted); }
            .compact-list { margin-top: 14px; }
            table { width:100%; border-collapse:collapse; table-layout:fixed; background:white; }
            th, td { border-bottom:1px solid #d9e3ee; padding:10px; text-align:left; overflow-wrap:anywhere; }
            th:last-child, td:last-child { text-align:right; }
            th { color: var(--muted); background:#f8fafc; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
            .stamp-wrap { display:flex; align-items:flex-end; }
            .due-stamp, .paid-stamp { padding: 10px 26px; border: 3px solid currentColor; border-radius: 12px; font-size: 42px; font-weight: 800; text-transform: uppercase; }
            .due-stamp { color: #b91c1c; }
            .paid-stamp { color: #166534; }
            .prepared-by { text-align:right; display:grid; gap:4px; }
            .page-break { page-break-before: always; }
            @media (max-width: 920px) {
              body { padding: 12px; }
              .detail-grid { grid-template-columns:1fr; }
            }
            @media print {
              body { margin:0; padding:0; background:white; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
              .preview-shell { max-width:none; padding:0; }
              .invoice-copy { box-shadow:none; border-radius:0; border:0; padding:0; }
              .page-break { page-break-before: always; }
              @page { size:A4 portrait; margin:12mm; }
            }
          </style>
        </head>
        <body>
          <div class="preview-shell">
            ${renderCopy('Patient Copy')}
            <div class="page-break"></div>
            ${renderCopy('Office Copy')}
          </div>
        </body>
      </html>
    `;
  }

  loadInvoiceDetail(invoiceId: string, openPreview = false): void {
    this.billingService.getInvoice(invoiceId).subscribe((invoice) => {
      this.latestInvoice = invoice;
      this.syncPaymentForm(invoice);
      this.syncRefundForm(invoice);
      if (openPreview) {
        this.openInvoicePreview(invoice);
      }
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

  private isDueInvoice(invoice: BillingInvoiceListItem): boolean {
    return invoice.status !== 'void' && Number(invoice.due_amount) > 0;
  }

  closeInvoicePreview(): void {
    this.invoicePreviewInvoice = null;
    this.invoicePreviewHtml = null;
    this.invoicePreviewUrl = null;
    this.releasePreviewUrl();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { printInvoice: null },
      queryParamsHandling: 'merge',
    });
  }

  printInvoicePreview(): void {
    const frameWindow = this.invoiceFrame?.nativeElement.contentWindow;
    if (!frameWindow) {
      return;
    }
    frameWindow.focus();
    frameWindow.print();
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
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

  private openInvoicePreview(invoice: BillingInvoice): void {
    this.invoicePreviewInvoice = invoice;
    this.invoicePreviewHtml = this.buildInvoicePrintHtml(invoice);
    this.invoicePreviewUrl = this.buildPreviewUrl(this.invoicePreviewHtml);
  }

  private buildPreviewUrl(html: string): SafeResourceUrl {
    this.releasePreviewUrl();
    const objectUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    this.invoicePreviewObjectUrl = objectUrl;
    return this.sanitizer.bypassSecurityTrustResourceUrl(objectUrl);
  }

  private releasePreviewUrl(): void {
    if (!this.invoicePreviewObjectUrl) {
      return;
    }
    URL.revokeObjectURL(this.invoicePreviewObjectUrl);
    this.invoicePreviewObjectUrl = null;
  }

  private getPatientAgeLabel(dateOfBirth?: string | null): string {
    if (!dateOfBirth) {
      return '-';
    }
    const birthDate = new Date(dateOfBirth);
    if (Number.isNaN(birthDate.getTime())) {
      return '-';
    }
    const now = new Date();
    let years = now.getFullYear() - birthDate.getFullYear();
    const monthDelta = now.getMonth() - birthDate.getMonth();
    if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birthDate.getDate())) {
      years -= 1;
    }
    return years >= 0 ? `${years}` : '-';
  }

  private amountInWords(value: number): string {
    const whole = Math.floor(Math.abs(value));
    if (whole === 0) {
      return 'Zero';
    }
    const ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
    const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
    const scales = ['', 'thousand', 'million', 'billion'];
    const chunkToWords = (chunk: number): string => {
      const parts: string[] = [];
      const hundreds = Math.floor(chunk / 100);
      const remainder = chunk % 100;
      if (hundreds) {
        parts.push(`${ones[hundreds]} hundred`);
      }
      if (remainder >= 20) {
        const ten = Math.floor(remainder / 10);
        const unit = remainder % 10;
        parts.push(unit ? `${tens[ten]}-${ones[unit]}` : tens[ten]);
      } else if (remainder > 0) {
        parts.push(ones[remainder]);
      }
      return parts.join(' ');
    };
    const words: string[] = [];
    let remaining = whole;
    let scaleIndex = 0;
    while (remaining > 0 && scaleIndex < scales.length) {
      const chunk = remaining % 1000;
      if (chunk) {
        const chunkWords = chunkToWords(chunk);
        words.unshift(scales[scaleIndex] ? `${chunkWords} ${scales[scaleIndex]}` : chunkWords);
      }
      remaining = Math.floor(remaining / 1000);
      scaleIndex += 1;
    }
    return words.join(' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }
}
