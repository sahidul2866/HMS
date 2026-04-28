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
