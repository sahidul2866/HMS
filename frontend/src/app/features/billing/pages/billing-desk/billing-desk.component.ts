import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { UiStateService } from '../../../../core/services/ui-state.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import {
  BillingInvoice,
  BillingInvoiceFilters,
  BillingInvoiceItemPayload,
  BillingInvoiceListItem,
  BillingInvoicePreview,
  BillingService,
  CreateBillingInvoicePayload,
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
  private readonly patientService = inject(PatientService);
  private readonly billingService = inject(BillingServiceApi);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);
  private readonly uiStateService = inject(UiStateService);
  readonly sessionService = inject(SessionService);

  patients: Patient[] = [];
  billingServices: BillingService[] = [];
  internalReferralDoctors: User[] = [];
  recentInvoices: BillingInvoiceListItem[] = [];
  latestInvoice: BillingInvoice | null = null;
  preview: BillingInvoicePreview | null = null;
  saving = false;
  previewMessage = '';

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    internal_referral_user_id: [''],
    discount_percentage: [0, [Validators.min(0), Validators.max(100)]],
    note: [''],
    items: this.fb.array([]),
  });

  readonly invoiceFilterForm = this.fb.group({
    q: [''],
    internal_referral_user_id: [''],
    status: [''],
    date_from: [''],
    date_to: [''],
  });

  constructor() {
    this.restoreState();
    if (!this.items.length) {
      this.addItem();
    }
    this.loadPatients();
    this.loadServices();
    this.loadDoctors();
    this.loadInvoices();
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      if (patientId) {
        this.form.patchValue({ patient_id: patientId });
        this.persistState();
      }
    });
    this.form.valueChanges.subscribe(() => this.persistState());
    this.invoiceFilterForm.valueChanges.subscribe(() => this.persistState());
  }

  get items(): FormArray {
    return this.form.controls.items as FormArray;
  }

  addItem(): void {
    this.items.push(
      this.fb.group({
        billing_service_id: ['', Validators.required],
        quantity: [1, [Validators.required, Validators.min(0.01)]],
      })
    );
    this.persistState();
  }

  removeItem(index: number): void {
    if (this.items.length === 1) {
      return;
    }
    this.items.removeAt(index);
    this.persistState();
    this.recalculatePreview();
  }

  loadPatients(): void {
    this.patientService.list().subscribe((patients) => (this.patients = patients));
  }

  loadServices(): void {
    this.billingService.listServices().subscribe((services) => {
      this.billingServices = services;
      this.recalculatePreview();
    });
  }

  loadDoctors(): void {
    this.doctorDirectoryService.listDoctors(true).subscribe((doctors) => (this.internalReferralDoctors = doctors));
  }

  loadInvoices(): void {
    this.billingService.listInvoices(this.getInvoiceFilters()).subscribe((invoices) => (this.recentInvoices = invoices));
  }

  onBillingItemChanged(): void {
    this.recalculatePreview();
  }

  recalculatePreview(): void {
    const items = this.getInvoiceItemsPayload();
    if (!items.length) {
      this.preview = null;
      return;
    }

    const discount = Number(this.form.getRawValue().discount_percentage ?? 0);
    this.billingService.previewInvoice(discount, items).subscribe({
      next: (preview) => {
        this.preview = preview;
        this.previewMessage = '';
      },
      error: () => {
        this.preview = null;
        this.previewMessage = 'Preview unavailable until all selected services are valid.';
      },
    });
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/billing' } });
  }

  submit(): void {
    if (this.form.invalid || this.saving) {
      return;
    }

    const payload: CreateBillingInvoicePayload = {
      patient_id: this.form.getRawValue().patient_id ?? '',
      internal_referral_user_id: this.form.getRawValue().internal_referral_user_id || null,
      discount_percentage: Number(this.form.getRawValue().discount_percentage ?? 0),
      note: this.form.getRawValue().note || null,
      items: this.getInvoiceItemsPayload(),
    };
    if (!payload.items.length) {
      return;
    }

    this.saving = true;
    this.billingService.createInvoice(payload).subscribe({
      next: (invoice) => {
        this.saving = false;
        this.latestInvoice = invoice;
        this.loadInvoices();
        this.notificationService.success(`Invoice ${invoice.invoice_number} created successfully.`);
        this.form.reset({
          patient_id: this.form.getRawValue().patient_id ?? '',
          internal_referral_user_id: '',
          discount_percentage: 0,
          note: '',
        });
        this.items.clear();
        this.addItem();
        this.preview = null;
        this.persistState();
      },
      error: () => {
        this.saving = false;
      },
    });
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
            ${invoice.void_reason ? `<div><strong>Void Reason</strong><span>${invoice.void_reason}</span></div>` : ''}
          </div>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  }

  formatPatient(patient: Patient): string {
    return `${patient.patient_number} - ${patient.first_name} ${patient.last_name}`;
  }

  onInternalReferralChanged(): void {
    const userId = this.form.getRawValue().internal_referral_user_id;
    if (!this.internalReferralDoctors.find((item) => item.id === userId)) {
      this.form.patchValue({ internal_referral_user_id: '' });
    }
  }

  loadInvoiceDetail(invoiceId: string): void {
    this.billingService.getInvoice(invoiceId).subscribe((invoice) => {
      this.latestInvoice = invoice;
      this.notificationService.info(`Loaded invoice ${invoice.invoice_number}.`);
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

  formatStatus(status: string): string {
    return status.replace('_', ' ').toUpperCase();
  }

  getServiceName(serviceId: string): string {
    return this.billingServices.find((service) => service.id === serviceId)?.name ?? 'Select service';
  }

  getServiceAmount(serviceId: string, quantity: number): string {
    const service = this.billingServices.find((item) => item.id === serviceId);
    if (!service) {
      return this.formatCurrency(0);
    }
    return this.formatCurrency(Number(service.unit_price) * quantity);
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  private getInvoiceItemsPayload(): BillingInvoiceItemPayload[] {
    const rawItems = this.items.getRawValue() as { billing_service_id?: string; quantity?: number }[];
    return rawItems
      .filter((item) => item.billing_service_id && Number(item.quantity) > 0)
      .map((item) => ({
        billing_service_id: item.billing_service_id!,
        quantity: Number(item.quantity),
      }));
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
    const state = this.uiStateService.load<{
      form?: {
        patient_id?: string;
        internal_referral_user_id?: string;
        discount_percentage?: number;
        note?: string;
        items?: BillingInvoiceItemPayload[];
      };
      filters?: BillingInvoiceFilters;
    }>(BillingDeskComponent.STATE_KEY);

    if (!state) {
      return;
    }

    if (state.form) {
      this.form.patchValue({
        patient_id: state.form.patient_id ?? '',
        internal_referral_user_id: state.form.internal_referral_user_id ?? '',
        discount_percentage: state.form.discount_percentage ?? 0,
        note: state.form.note ?? '',
      });

      this.items.clear();
      for (const item of state.form.items ?? []) {
        this.items.push(
          this.fb.group({
            billing_service_id: [item.billing_service_id, Validators.required],
            quantity: [item.quantity, [Validators.required, Validators.min(0.01)]],
          })
        );
      }
    }

    if (state.filters) {
      this.invoiceFilterForm.patchValue({
        q: state.filters.q ?? '',
        internal_referral_user_id: state.filters.internal_referral_user_id ?? '',
        status: state.filters.status ?? '',
        date_from: state.filters.date_from ?? '',
        date_to: state.filters.date_to ?? '',
      });
    }
  }

  private persistState(): void {
    this.uiStateService.save(BillingDeskComponent.STATE_KEY, {
      form: {
        patient_id: this.form.getRawValue().patient_id ?? '',
        internal_referral_user_id: this.form.getRawValue().internal_referral_user_id ?? '',
        discount_percentage: Number(this.form.getRawValue().discount_percentage ?? 0),
        note: this.form.getRawValue().note ?? '',
        items: this.getInvoiceItemsPayload(),
      },
      filters: this.getInvoiceFilters(),
    });
  }
}
