import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { PharmacyCustomer, PharmacyReturn, PharmacySale } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-sales-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-sales-list.component.html',
  styleUrls: ['./pharmacy-sales-list.component.scss'],
})
export class PharmacySalesListComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);

  sales: PharmacySale[] = [];
  customers: PharmacyCustomer[] = [];
  selectedSale: PharmacySale | null = null;
  search = '';
  customerFilter = '';
  statusFilter = '';
  page = 1;
  pageSize = 10;
  total = 0;

  readonly returnForm = this.fb.group({
    sale_item_id: ['', Validators.required],
    returned_at: [new Date().toISOString().slice(0, 10), Validators.required],
    quantity: [1, Validators.required],
    note: [''],
  });

  constructor() {
    this.loadCustomers();
    this.loadPage();
    this.route.queryParamMap.subscribe((params) => {
      const saleId = params.get('saleId');
      if (saleId) {
        this.pharmacyService.getSale(saleId).subscribe((sale) => {
          this.selectedSale = sale;
          this.returnForm.patchValue({ sale_item_id: sale.items[0]?.id || '' });
        });
      }
    });
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  loadCustomers(): void {
    this.pharmacyService.listCustomers({ page: 1, page_size: 100 }).subscribe((response) => (this.customers = response.items));
  }

  loadPage(): void {
    this.pharmacyService
      .listSales({
        page: this.page,
        page_size: this.pageSize,
        q: this.search || undefined,
        customer_id: this.customerFilter || undefined,
        status: this.statusFilter || undefined,
      })
      .subscribe((response) => {
        this.sales = response.items;
        this.total = response.total;
        this.page = response.page;
      });
  }

  searchNow(): void {
    this.page = 1;
    this.loadPage();
  }

  openSale(sale: PharmacySale): void {
    this.selectedSale = sale;
    this.returnForm.patchValue({ sale_item_id: sale.items[0]?.id || '', quantity: 1 });
  }

  navigateToEdit(sale: PharmacySale): void {
    void this.router.navigate(['/pharmacy/sales'], { queryParams: { saleId: sale.id } });
  }

  deleteSale(sale: PharmacySale): void {
    if (!window.confirm(`Delete sale ${sale.sale_number}?`)) {
      return;
    }
    this.pharmacyService.deleteSale(sale.id).subscribe(() => {
      this.notificationService.success('Sale deleted successfully.');
      this.selectedSale = this.selectedSale?.id === sale.id ? null : this.selectedSale;
      this.loadPage();
    });
  }

  submitReturn(): void {
    if (!this.selectedSale || this.returnForm.invalid) {
      this.returnForm.markAllAsTouched();
      return;
    }
    const payload = { ...this.returnForm.getRawValue(), sale_id: this.selectedSale.id };
    this.pharmacyService.createReturn(payload as never).subscribe((returnRecord: PharmacyReturn) => {
      this.notificationService.success(`Return ${returnRecord.return_number} created successfully.`);
      this.pharmacyService.getSale(this.selectedSale!.id).subscribe((sale) => (this.selectedSale = sale));
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
