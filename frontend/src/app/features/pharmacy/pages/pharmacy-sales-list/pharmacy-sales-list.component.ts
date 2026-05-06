import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { ActionConfirmationService } from '../../../../core/services/action-confirmation.service';
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
  private readonly confirmationService = inject(ActionConfirmationService);

  sales: PharmacySale[] = [];
  customers: PharmacyCustomer[] = [];
  selectedSale: PharmacySale | null = null;
  search = '';
  customerFilter = '';
  statusFilter = '';
  page = 1;
  pageSize = 10;
  total = 0;
  sortField: 'sale_number' | 'customer' | 'status' | 'subtotal' | 'net_payable' | 'sale_date' = 'sale_date';
  sortDirection: 'asc' | 'desc' = 'desc';
  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

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

  onFiltersChanged(): void {
    this.page = 1;
    if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = setTimeout(() => this.loadPage(), 250);
  }

  toggleSort(field: PharmacySalesListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'sale_date' ? 'desc' : 'asc';
  }

  sortClass(field: PharmacySalesListComponent['sortField']): string {
    return this.sortField === field ? `sorted-${this.sortDirection}` : '';
  }

  get displayedSales(): PharmacySale[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.sales].sort((a, b) => {
      switch (this.sortField) {
        case 'sale_number':
          return dir * a.sale_number.localeCompare(b.sale_number);
        case 'customer':
          return dir * (a.customer_name || '').localeCompare(b.customer_name || '');
        case 'status':
          return dir * (a.status || '').localeCompare(b.status || '');
        case 'subtotal':
          return dir * (Number(a.subtotal || 0) - Number(b.subtotal || 0));
        case 'net_payable':
          return dir * (Number(a.net_payable || 0) - Number(b.net_payable || 0));
        case 'sale_date':
        default:
          return dir * ((a.sale_date || '').localeCompare(b.sale_date || ''));
      }
    });
  }

  exportCsv(): void {
    const header = ['Sale No', 'Customer', 'Status', 'Subtotal', 'Net Payable', 'Date'];
    const rows = this.displayedSales.map((sale) => [
      sale.sale_number,
      sale.customer_name || '',
      sale.status,
      sale.subtotal,
      sale.net_payable,
      sale.sale_date || '',
    ]);
    const csv = [header, ...rows].map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'medicine-sales.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  openSale(sale: PharmacySale): void {
    this.selectedSale = sale;
    this.returnForm.patchValue({ sale_item_id: sale.items[0]?.id || '', quantity: 1 });
  }

  navigateToEdit(sale: PharmacySale): void {
    void this.router.navigate(['/pharmacy/sales'], { queryParams: { saleId: sale.id } });
  }

  deleteSale(sale: PharmacySale): void {
    if (!this.confirmationService.confirmDestructive(sale.sale_number, 'delete sale')) {
      return;
    }
    this.pharmacyService.deleteSale(sale.id).subscribe(() => {
      this.notificationService.success(`Sale ${sale.sale_number} deleted.`);
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
      this.notificationService.success(`Return ${returnRecord.return_number} created. Sale balance and return history are refreshed.`);
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
