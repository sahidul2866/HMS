import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { PharmacyReturn } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-returns',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-returns.component.html',
  styleUrls: ['./pharmacy-returns.component.scss'],
})
export class PharmacyReturnsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);

  returns: PharmacyReturn[] = [];
  selectedReturn: PharmacyReturn | null = null;
  search = '';
  page = 1;
  pageSize = 10;
  total = 0;
  sortField: 'return_number' | 'sale_number' | 'customer' | 'medicine' | 'quantity' | 'total_amount' | 'returned_at' = 'returned_at';
  sortDirection: 'asc' | 'desc' = 'desc';
  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  readonly form = this.fb.group({
    returned_at: ['', Validators.required],
    quantity: [1, Validators.required],
    note: [''],
  });

  constructor() {
    this.loadPage();
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  loadPage(): void {
    this.pharmacyService.listReturns({ page: this.page, page_size: this.pageSize, q: this.search || undefined }).subscribe((response) => {
      this.returns = response.items;
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

  toggleSort(field: PharmacyReturnsComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'returned_at' ? 'desc' : 'asc';
  }

  get displayedReturns(): PharmacyReturn[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.returns].sort((a, b) => {
      switch (this.sortField) {
        case 'return_number':
          return dir * a.return_number.localeCompare(b.return_number);
        case 'sale_number':
          return dir * (a.sale_number || '').localeCompare(b.sale_number || '');
        case 'customer':
          return dir * (a.customer_name || '').localeCompare(b.customer_name || '');
        case 'medicine':
          return dir * (a.medicine_name || '').localeCompare(b.medicine_name || '');
        case 'quantity':
          return dir * (Number(a.quantity || 0) - Number(b.quantity || 0));
        case 'total_amount':
          return dir * (Number(a.total_amount || 0) - Number(b.total_amount || 0));
        case 'returned_at':
        default:
          return dir * (a.returned_at || '').localeCompare(b.returned_at || '');
      }
    });
  }

  selectReturn(item: PharmacyReturn): void {
    this.selectedReturn = item;
    this.form.patchValue({
      returned_at: item.returned_at,
      quantity: Number(item.quantity),
      note: item.note || '',
    });
  }

  updateReturn(): void {
    if (!this.selectedReturn || this.form.invalid) {
      return;
    }
    const payload = {
      sale_id: this.selectedReturn.sale_id,
      sale_item_id: this.selectedReturn.sale_item_id,
      ...this.form.getRawValue(),
    };
    this.pharmacyService.updateReturn(this.selectedReturn.id, payload as never).subscribe((item) => {
      this.notificationService.success(`Return ${item.return_number} updated successfully.`);
      this.selectedReturn = item;
      this.loadPage();
    });
  }

  deleteReturn(item: PharmacyReturn): void {
    if (!window.confirm(`Delete return ${item.return_number}?`)) {
      return;
    }
    this.pharmacyService.deleteReturn(item.id).subscribe(() => {
      this.notificationService.success('Return deleted successfully.');
      this.selectedReturn = this.selectedReturn?.id === item.id ? null : this.selectedReturn;
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
}
