import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormArray, FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { PharmacyCustomer, PharmacyMedicine, PharmacySale, PharmacySalesDraft } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-sales-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-sales-editor.component.html',
  styleUrls: ['./pharmacy-sales-editor.component.scss'],
})
export class PharmacySalesEditorComponent {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);

  customers: PharmacyCustomer[] = [];
  medicines: PharmacyMedicine[] = [];
  editingSale: PharmacySale | null = null;
  draft: PharmacySalesDraft | null = null;

  readonly form = this.fb.group({
    customer_id: [''],
    patient_id: [''],
    source_visit_id: [''],
    sale_date: [new Date().toISOString().slice(0, 10), Validators.required],
    discount_amount: [0, Validators.required],
    note: [''],
    items: this.fb.array([]),
  });

  constructor() {
    this.loadReferenceData();
    this.addItem();
    this.route.queryParamMap.subscribe((params) => {
      const saleId = params.get('saleId');
      const opdVisitId = params.get('opdVisitId');
      const medicineId = params.get('medicineId');
      const customerId = params.get('customerId');
      if (saleId) {
        this.pharmacyService.getSale(saleId).subscribe((sale) => this.applySale(sale));
      } else if (opdVisitId) {
        this.loadDraft(opdVisitId);
      } else {
        this.editingSale = null;
        this.draft = null;
        if (customerId) {
          this.form.patchValue({ customer_id: customerId });
        }
        if (medicineId) {
          this.applyMedicineQuery(medicineId);
        }
      }
    });
  }

  get items(): FormArray {
    return this.form.controls.items as FormArray;
  }

  addItem(): void {
    this.items.push(
      this.fb.group({
        medicine_id: ['', Validators.required],
        source_visit_order_id: [''],
        batch_no: [''],
        expiry_date: [''],
        quantity: [1, [Validators.required, Validators.min(0.01)]],
        unit_price: [0, Validators.min(0)],
        note: [''],
      }),
    );
  }

  removeItem(index: number): void {
    if (this.items.length === 1) {
      return;
    }
    this.items.removeAt(index);
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const payload = this.form.getRawValue();
    const request = this.editingSale
      ? this.pharmacyService.updateSale(this.editingSale.id, payload as never)
      : this.pharmacyService.createSale(payload as never);
    request.subscribe((sale) => {
      this.notificationService.success(`Medicine sale ${this.editingSale ? 'updated' : 'created'} successfully.`);
      this.resetForm();
      void this.router.navigate(['/pharmacy/sales/list'], { queryParams: { saleId: sale.id } });
    });
  }

  resetForm(): void {
    this.editingSale = null;
    this.draft = null;
    this.form.reset({
      customer_id: '',
      patient_id: '',
      source_visit_id: '',
      sale_date: new Date().toISOString().slice(0, 10),
      discount_amount: 0,
      note: '',
      items: [],
    });
    this.items.clear();
    this.addItem();
    void this.router.navigate([], { relativeTo: this.route, queryParams: { saleId: null, opdVisitId: null }, queryParamsHandling: 'merge' });
  }

  selectedMedicinePrice(index: number): number {
    const medicineId = this.items.at(index).get('medicine_id')?.value;
    return Number(this.medicines.find((item) => item.id === medicineId)?.sale_price ?? 0);
  }

  onMedicineChanged(index: number): void {
    const control = this.items.at(index);
    control.patchValue({ unit_price: this.selectedMedicinePrice(index) });
  }

  get subtotal(): number {
    return this.items.controls.reduce((sum, control) => {
      const quantity = Number(control.get('quantity')?.value ?? 0);
      const unitPrice = Number(control.get('unit_price')?.value ?? 0);
      return sum + quantity * unitPrice;
    }, 0);
  }

  get netPayable(): number {
    return Math.max(this.subtotal - Number(this.form.getRawValue().discount_amount ?? 0), 0);
  }

  private loadReferenceData(): void {
    this.pharmacyService.listCustomers({ page: 1, page_size: 100 }).subscribe((response) => (this.customers = response.items));
    this.pharmacyService.listMedicines({ page: 1, page_size: 100 }).subscribe((response) => {
      this.medicines = response.items;
      const medicineId = this.route.snapshot.queryParamMap.get('medicineId');
      if (medicineId) {
        this.applyMedicineQuery(medicineId);
      }
    });
  }

  private applyMedicineQuery(medicineId: string): void {
    const first = this.items.at(0);
    if (!first) {
      return;
    }
    first.patchValue({ medicine_id: medicineId });
    this.onMedicineChanged(0);
  }

  private applySale(sale: PharmacySale): void {
    this.editingSale = sale;
    this.draft = null;
    this.items.clear();
    for (const item of sale.items) {
      this.items.push(
        this.fb.group({
          medicine_id: [item.medicine_id, Validators.required],
          source_visit_order_id: [item.source_visit_order_id || ''],
          batch_no: [item.batch_no || ''],
          expiry_date: [item.expiry_date || ''],
          quantity: [Number(item.quantity), [Validators.required, Validators.min(0.01)]],
          unit_price: [Number(item.unit_price), Validators.min(0)],
          note: [item.note || ''],
        }),
      );
    }
    this.form.patchValue({
      customer_id: sale.customer_id,
      patient_id: sale.patient_id || '',
      source_visit_id: sale.source_visit_id || '',
      sale_date: sale.sale_date,
      discount_amount: Number(sale.discount_amount),
      note: sale.note || '',
    });
  }

  private loadDraft(visitId: string): void {
    this.pharmacyService.getSaleDraftFromVisit(visitId).subscribe({
      next: (draft) => {
        this.draft = draft;
        this.editingSale = null;
        this.items.clear();
        for (const item of draft.items) {
          const suggested = item.medicine_suggestions[0];
          this.items.push(
            this.fb.group({
              medicine_id: [suggested?.medicine_id || '', Validators.required],
              source_visit_order_id: [item.source_visit_order_id],
              batch_no: [''],
              expiry_date: [''],
              quantity: [Number(item.quantity), [Validators.required, Validators.min(0.01)]],
              unit_price: [Number(suggested?.sale_price || 0), Validators.min(0)],
              note: [item.instruction || item.warning || ''],
            }),
          );
        }
        this.form.patchValue({
          customer_id: draft.customer_id || '',
          patient_id: draft.patient_id,
          source_visit_id: draft.source_visit_id,
          sale_date: new Date().toISOString().slice(0, 10),
          discount_amount: 0,
          note: draft.note || '',
        });
      },
      error: () => {
        this.notificationService.warning('Pharmacy sales draft is no longer available for this OPD visit.');
        this.draft = null;
        this.resetForm();
      },
    });
  }
}
