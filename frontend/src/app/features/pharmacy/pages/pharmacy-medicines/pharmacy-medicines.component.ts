import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { PharmacyCompany, PharmacyGeneric, PharmacyMedicine, PharmacyMedicineType } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-medicines',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-medicines.component.html',
  styleUrls: ['./pharmacy-medicines.component.scss'],
})
export class PharmacyMedicinesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  medicines: PharmacyMedicine[] = [];
  medicineTypes: PharmacyMedicineType[] = [];
  generics: PharmacyGeneric[] = [];
  companies: PharmacyCompany[] = [];

  search = '';
  typeFilter = '';
  companyFilter = '';
  lowStockOnly = false;
  page = 1;
  pageSize = 10;
  total = 0;
  editingId: string | null = null;
  sortField: 'name' | 'type' | 'generic' | 'company' | 'stock' | 'sale_price' = 'name';
  sortDirection: 'asc' | 'desc' = 'asc';
  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  readonly form = this.fb.group({
    medicine_type_id: ['', Validators.required],
    generic_id: ['', Validators.required],
    company_id: ['', Validators.required],
    name: ['', Validators.required],
    strength: [''],
    dosage_form: [''],
    sku: [''],
    barcode: [''],
    purchase_price: [0, Validators.required],
    sale_price: [0, Validators.required],
    reorder_level: [0, Validators.required],
    description: [''],
  });

  constructor() {
    this.loadReferenceData();
    this.loadPage();
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  loadReferenceData(): void {
    this.pharmacyService.listMedicineTypes({ page: 1, page_size: 100 }).subscribe((response) => (this.medicineTypes = response.items));
    this.pharmacyService.listGenerics({ page: 1, page_size: 100 }).subscribe((response) => (this.generics = response.items));
    this.pharmacyService.listCompanies({ page: 1, page_size: 100 }).subscribe((response) => (this.companies = response.items));
  }

  loadPage(): void {
    this.pharmacyService
      .listMedicines({
        page: this.page,
        page_size: this.pageSize,
        q: this.search || undefined,
        medicine_type_id: this.typeFilter || undefined,
        company_id: this.companyFilter || undefined,
        low_stock: this.lowStockOnly || undefined,
      })
      .subscribe((response) => {
        this.medicines = response.items;
        this.total = response.total;
        this.page = response.page;
      });
  }

  searchNow(): void {
    this.page = 1;
    this.loadPage();
  }

  onFiltersChanged(): void {
    this.page = 1;
    if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = setTimeout(() => this.loadPage(), 250);
  }

  toggleSort(field: PharmacyMedicinesComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = 'asc';
  }

  get displayedMedicines(): PharmacyMedicine[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.medicines].sort((a, b) => {
      switch (this.sortField) {
        case 'type':
          return dir * (a.medicine_type_name || '').localeCompare(b.medicine_type_name || '');
        case 'generic':
          return dir * (a.generic_name || '').localeCompare(b.generic_name || '');
        case 'company':
          return dir * (a.company_name || '').localeCompare(b.company_name || '');
        case 'stock':
          return dir * (Number(a.stock_quantity || 0) - Number(b.stock_quantity || 0));
        case 'sale_price':
          return dir * (Number(a.sale_price || 0) - Number(b.sale_price || 0));
        case 'name':
        default:
          return dir * (a.name || '').localeCompare(b.name || '');
      }
    });
  }

  edit(item: PharmacyMedicine): void {
    this.editingId = item.id;
    this.form.reset({
      medicine_type_id: item.medicine_type_id,
      generic_id: item.generic_id,
      company_id: item.company_id,
      name: item.name,
      strength: item.strength || '',
      dosage_form: item.dosage_form || '',
      sku: item.sku || '',
      barcode: item.barcode || '',
      purchase_price: Number(item.purchase_price),
      sale_price: Number(item.sale_price),
      reorder_level: Number(item.reorder_level),
      description: item.description || '',
    });
  }

  resetForm(): void {
    this.editingId = null;
    this.form.reset({
      medicine_type_id: '',
      generic_id: '',
      company_id: '',
      name: '',
      strength: '',
      dosage_form: '',
      sku: '',
      barcode: '',
      purchase_price: 0,
      sale_price: 0,
      reorder_level: 0,
      description: '',
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const payload = this.form.getRawValue();
    const request = this.editingId
      ? this.pharmacyService.updateMedicine(this.editingId, payload as never)
      : this.pharmacyService.createMedicine(payload as never);
    request.subscribe(() => {
      this.notificationService.success(`Medicine ${this.editingId ? 'updated' : 'created'} successfully.`);
      this.resetForm();
      this.loadPage();
    });
  }

  remove(item: PharmacyMedicine): void {
    if (!window.confirm(`Delete ${item.name}?`)) {
      return;
    }
    this.pharmacyService.deleteMedicine(item.id).subscribe(() => {
      this.notificationService.success('Medicine deleted successfully.');
      this.loadPage();
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

  isLowStock(item: PharmacyMedicine): boolean {
    return Number(item.stock_quantity) <= Number(item.reorder_level);
  }

  openPurchase(item: PharmacyMedicine): void {
    void this.router.navigate(['/pharmacy/purchases'], { queryParams: { medicineId: item.id } });
  }

  openSale(item: PharmacyMedicine): void {
    void this.router.navigate(['/pharmacy/sales'], { queryParams: { medicineId: item.id } });
  }
}
