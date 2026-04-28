import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { BillingInvoice, BillingInvoiceItem, BillingInvoiceListItem } from '../../../billing/models/billing.models';
import { BillingServiceApi } from '../../../billing/services/billing.service';
import { PharmacyDispense, PharmacyPendingPrescription } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-workbench',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './pharmacy-workbench.component.html',
  styleUrls: ['./pharmacy-workbench.component.scss'],
})
export class PharmacyWorkbenchComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly billingService = inject(BillingServiceApi);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  invoices: BillingInvoiceListItem[] = [];
  dispenses: PharmacyDispense[] = [];
  pendingPrescriptions: PharmacyPendingPrescription[] = [];
  selectedPrescription: PharmacyPendingPrescription | null = null;
  selectedInvoice: BillingInvoiceListItem | null = null;
  selectedInvoiceDetail: BillingInvoice | null = null;
  selectedInvoiceItem: BillingInvoiceItem | null = null;
  returnTarget: PharmacyDispense | null = null;
  resultMessage = '';
  loading = true;

  readonly form = this.fb.group({
    billing_invoice_id: [''],
    source_visit_id: [''],
    source_visit_order_id: [''],
    patient_id: [''],
    prescription_ref: [''],
    medicine_name: ['', Validators.required],
    quantity: [1, Validators.required],
    unit_price: [0, Validators.required],
    note: [''],
  });

  readonly returnForm = this.fb.group({
    quantity: [1, [Validators.required, Validators.min(0.01)]],
    note: [''],
  });

  constructor() {
    this.loadAll();
  }

  loadAll(): void {
    this.loading = true;
    this.pharmacyService.list().subscribe((dispenses) => {
      this.dispenses = dispenses;
      this.billingService.listInvoices({ status: 'posted' }).subscribe((invoices) => {
        this.invoices = invoices.slice(0, 20);
        this.pharmacyService.listPendingPrescriptions().subscribe((orders) => {
          this.pendingPrescriptions = orders;
          this.applyRouteContext();
          this.loading = false;
        });
      });
    });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const payload = this.form.getRawValue();
    this.pharmacyService.dispense(payload as never).subscribe({
      next: (result) => {
        this.resultMessage = `Issued ${result.quantity} of ${result.medicine_name}. Prescription balance updated.`;
        this.resetForm();
        this.loadAll();
        this.notificationService.success(`Dispensed ${result.medicine_name} successfully.`);
      },
    });
  }

  onInvoiceChanged(): void {
    const invoiceId = this.form.getRawValue().billing_invoice_id;
    const invoice = this.invoices.find((item) => item.id === invoiceId);
    if (!invoice) {
      this.selectedInvoice = null;
      return;
    }
    this.applyInvoice(invoice);
  }

  onPrescriptionChanged(): void {
    const orderId = this.form.getRawValue().source_visit_order_id;
    const prescription = this.pendingPrescriptions.find((item) => item.order_id === orderId);
    if (!prescription) {
      this.selectedPrescription = null;
      return;
    }
    this.applyPrescription(prescription);
  }

  applyInvoice(invoice: BillingInvoiceListItem): void {
    this.selectedInvoice = invoice;
    this.selectedInvoiceDetail = null;
    this.selectedInvoiceItem = null;
    this.selectedPrescription = null;
    this.form.patchValue({
      billing_invoice_id: invoice.id,
      source_visit_id: '',
      source_visit_order_id: '',
      patient_id: invoice.patient_id,
      prescription_ref: invoice.invoice_number,
      medicine_name: '',
      quantity: 1,
      unit_price: 0,
      note: `Linked to billing invoice ${invoice.invoice_number} for ${invoice.patient.first_name} ${invoice.patient.last_name}`,
    });
    this.billingService.getInvoice(invoice.id).subscribe((detail) => this.applyInvoiceDetail(detail));
  }

  applyInvoiceMedicineItem(item: BillingInvoiceItem): void {
    if (!this.selectedInvoiceDetail) {
      return;
    }
    this.selectedInvoiceItem = item;
    this.form.patchValue({
      billing_invoice_id: this.selectedInvoiceDetail.id,
      source_visit_id: this.selectedInvoiceDetail.source_opd_visit_id || '',
      source_visit_order_id: item.source_opd_visit_order_id || '',
      patient_id: this.selectedInvoiceDetail.patient_id,
      prescription_ref: this.selectedInvoiceDetail.invoice_number,
      medicine_name: item.service_name,
      quantity: Number(item.quantity || 1),
      unit_price: Number(item.unit_price || 0),
      note: `Dispense from billing invoice ${this.selectedInvoiceDetail.invoice_number}${item.source_label ? ` · ${item.source_label}` : ''}`,
    });
  }

  applyPrescription(prescription: PharmacyPendingPrescription): void {
    this.selectedPrescription = prescription;
    this.selectedInvoice = null;
    this.form.patchValue({
      billing_invoice_id: '',
      source_visit_order_id: prescription.order_id,
      source_visit_id: prescription.visit_id,
      patient_id: prescription.patient_id,
      prescription_ref: prescription.visit_number,
      medicine_name: prescription.item_name,
      quantity: Number(prescription.remaining_quantity || prescription.quantity),
      unit_price: this.form.getRawValue().unit_price ?? 0,
      note: `From OPD prescription ${prescription.visit_number} by ${prescription.doctor_name}${prescription.instructions ? ` · ${prescription.instructions}` : ''}`,
    });
  }

  prepareReturn(dispense: PharmacyDispense): void {
    this.returnTarget = dispense;
    this.returnForm.patchValue({
      quantity: Number(dispense.remaining_quantity),
      note: dispense.return_note || '',
    });
  }

  submitReturn(): void {
    if (!this.returnTarget || this.returnForm.invalid) {
      return;
    }
    const raw = this.returnForm.getRawValue();
    this.pharmacyService
      .returnDispense(this.returnTarget.id, {
        quantity: Number(raw.quantity ?? 0),
        note: raw.note?.trim() || null,
      })
      .subscribe((result) => {
        this.resultMessage = `Return posted for ${result.medicine_name}. Net issued quantity is now ${result.remaining_quantity}.`;
        this.returnTarget = null;
        this.returnForm.reset({ quantity: 1, note: '' });
        this.loadAll();
        this.notificationService.warning(`Return recorded for ${result.medicine_name}.`);
      });
  }

  resetForm(): void {
    this.selectedPrescription = null;
    this.selectedInvoice = null;
    this.selectedInvoiceDetail = null;
    this.selectedInvoiceItem = null;
    this.returnTarget = null;
    this.form.reset({
      billing_invoice_id: '',
      source_visit_id: '',
      source_visit_order_id: '',
      patient_id: '',
      prescription_ref: '',
      medicine_name: '',
      quantity: 1,
      unit_price: 0,
      note: '',
    });
    this.returnForm.reset({
      quantity: 1,
      note: '',
    });
  }

  openQueue(): void {
    void this.router.navigate(['/pharmacy/dispense']);
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value || 0));
  }

  private applyRouteContext(): void {
    this.route.queryParamMap.subscribe((params) => {
      const orderId = params.get('orderId');
      const invoiceId = params.get('invoiceId');
      const dispenseId = params.get('dispenseId');

      if (orderId) {
        const prescription = this.pendingPrescriptions.find((item) => item.order_id === orderId);
        if (prescription) {
          this.applyPrescription(prescription);
        }
      } else if (invoiceId) {
        const invoice = this.invoices.find((item) => item.id === invoiceId);
        if (invoice) {
          this.applyInvoice(invoice);
        }
      } else if (dispenseId) {
        const dispense = this.dispenses.find((item) => item.id === dispenseId);
        if (dispense) {
          this.prepareReturn(dispense);
        }
      }
    });
  }

  get invoicePharmacyItems(): BillingInvoiceItem[] {
    return (this.selectedInvoiceDetail?.items ?? []).filter((item) => (item.source_module || '').toLowerCase() === 'pharmacy');
  }

  private applyInvoiceDetail(detail: BillingInvoice): void {
    this.selectedInvoiceDetail = detail;
    const pharmacyItem = this.invoicePharmacyItems[0];
    if (pharmacyItem) {
      this.applyInvoiceMedicineItem(pharmacyItem);
    } else {
      this.resultMessage = `Invoice ${detail.invoice_number} has no medicine line to dispense.`;
    }
  }
}
