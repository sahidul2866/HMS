import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { PharmacyMedicine, PharmacyPurchase } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-purchases',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-purchases.component.html',
  styleUrls: ['./pharmacy-purchases.component.scss'],
})
export class PharmacyPurchasesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);

  purchases: PharmacyPurchase[] = [];
  medicines: PharmacyMedicine[] = [];
  search = '';
  medicineFilter = '';
  page = 1;
  pageSize = 10;
  total = 0;
  editingId: string | null = null;

  readonly form = this.fb.group({
    medicine_id: ['', Validators.required],
    purchase_date: [new Date().toISOString().slice(0, 10), Validators.required],
    supplier_name: [''],
    invoice_number: [''],
    batch_no: [''],
    expiry_date: [''],
    quantity: [0, [Validators.required, Validators.min(0.01)]],
    bonus_quantity: [0, [Validators.required, Validators.min(0)]],
    unit_cost: [0, [Validators.required, Validators.min(0.01)]],
    sale_price: [0, Validators.min(0)],
    note: [''],
  });

  constructor() {
    this.loadMedicines();
    this.loadPage();
    this.route.queryParamMap.subscribe((params) => {
      const medicineId = params.get('medicineId');
      if (medicineId) {
        this.form.patchValue({ medicine_id: medicineId });
      }
    });
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  loadMedicines(): void {
    this.pharmacyService.listMedicines({ page: 1, page_size: 100 }).subscribe((response) => (this.medicines = response.items));
  }

  loadPage(): void {
    this.pharmacyService
      .listPurchases({
        page: this.page,
        page_size: this.pageSize,
        q: this.search || undefined,
        medicine_id: this.medicineFilter || undefined,
      })
      .subscribe((response) => {
        this.purchases = response.items;
        this.total = response.total;
        this.page = response.page;
      });
  }

  searchNow(): void {
    this.page = 1;
    this.loadPage();
  }

  edit(item: PharmacyPurchase): void {
    this.editingId = item.id;
    this.form.reset({
      medicine_id: item.medicine_id,
      purchase_date: item.purchase_date,
      supplier_name: item.supplier_name || '',
      invoice_number: item.invoice_number || '',
      batch_no: item.batch_no || '',
      expiry_date: item.expiry_date || '',
      quantity: Number(item.quantity),
      bonus_quantity: Number(item.bonus_quantity),
      unit_cost: Number(item.unit_cost),
      sale_price: Number(item.sale_price || 0),
      note: item.note || '',
    });
  }

  resetForm(): void {
    this.editingId = null;
    this.form.reset({
      medicine_id: '',
      purchase_date: new Date().toISOString().slice(0, 10),
      supplier_name: '',
      invoice_number: '',
      batch_no: '',
      expiry_date: '',
      quantity: 0,
      bonus_quantity: 0,
      unit_cost: 0,
      sale_price: 0,
      note: '',
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const payload = this.form.getRawValue();
    const request = this.editingId
      ? this.pharmacyService.updatePurchase(this.editingId, payload as never)
      : this.pharmacyService.createPurchase(payload as never);
    request.subscribe(() => {
      this.notificationService.success(`Purchase ${this.editingId ? 'updated' : 'recorded'} successfully.`);
      this.resetForm();
      this.loadPage();
      this.loadMedicines();
    });
  }

  remove(item: PharmacyPurchase): void {
    if (!window.confirm(`Delete purchase ${item.purchase_number}?`)) {
      return;
    }
    this.pharmacyService.deletePurchase(item.id).subscribe(() => {
      this.notificationService.success('Purchase deleted successfully.');
      this.loadPage();
      this.loadMedicines();
    });
  }

  previousPage(): void {
    if (this.page <= 1) {
      return;
    }
    this.page -= 1;
    this.loadPage();
  }

  nextPage(): void {
    if (this.page >= this.totalPages) {
      return;
    }
    this.page += 1;
    this.loadPage();
  }

  formatCurrency(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT' }).format(Number(value ?? 0));
  }
}
