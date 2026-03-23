import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { BillingInvoiceListItem } from '../../../billing/models/billing.models';
import { BillingServiceApi } from '../../../billing/services/billing.service';
import { PharmacyDispense, PharmacyPendingPrescription } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-dispense',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './pharmacy-dispense.component.html',
})
export class PharmacyDispenseComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly billingService = inject(BillingServiceApi);
  private readonly notificationService = inject(NotificationService);

  dispenses: PharmacyDispense[] = [];
  invoices: BillingInvoiceListItem[] = [];
  pendingPrescriptions: PharmacyPendingPrescription[] = [];
  resultMessage = '';

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

  constructor() {
    this.loadDispenses();
    this.loadInvoices();
    this.loadPendingPrescriptions();
  }

  loadDispenses(): void {
    this.pharmacyService.list().subscribe((dispenses) => (this.dispenses = dispenses));
  }

  loadInvoices(): void {
    this.billingService.listInvoices({ status: 'posted' }).subscribe((invoices) => (this.invoices = invoices.slice(0, 20)));
  }

  loadPendingPrescriptions(): void {
    this.pharmacyService.listPendingPrescriptions().subscribe((orders) => (this.pendingPrescriptions = orders));
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const payload = this.form.getRawValue();
    this.pharmacyService.dispense(payload as never).subscribe({
      next: (result) => {
        this.resultMessage = `Dispensed ${result.medicine_name}. Total ${result.total_price}`;
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
        this.loadDispenses();
        this.loadPendingPrescriptions();
        this.notificationService.success(`Dispensed ${result.medicine_name} successfully.`);
      },
    });
  }

  onInvoiceChanged(): void {
    const invoiceId = this.form.getRawValue().billing_invoice_id;
    const invoice = this.invoices.find((item) => item.id === invoiceId);
    if (!invoice) {
      return;
    }
    this.form.patchValue({
      source_visit_id: '',
      source_visit_order_id: '',
      patient_id: invoice.patient_id,
      prescription_ref: invoice.invoice_number,
      note: `Linked to billing invoice ${invoice.invoice_number} for ${invoice.patient.first_name} ${invoice.patient.last_name}`,
    });
  }

  onPrescriptionChanged(): void {
    const orderId = this.form.getRawValue().source_visit_order_id;
    const prescription = this.pendingPrescriptions.find((item) => item.order_id === orderId);
    if (!prescription) {
      return;
    }
    this.form.patchValue({
      billing_invoice_id: '',
      source_visit_id: prescription.visit_id,
      patient_id: prescription.patient_id,
      prescription_ref: prescription.visit_number,
      medicine_name: prescription.item_name,
      quantity: Number(prescription.quantity),
      note: `From OPD prescription ${prescription.visit_number} by ${prescription.doctor_name}${prescription.instructions ? ` · ${prescription.instructions}` : ''}`,
    });
  }
}
