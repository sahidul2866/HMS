import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import {
  PharmacyDashboardSummary,
  PharmacyDispense,
  PharmacyMedicine,
  PharmacyPendingPrescription,
  PharmacyReturn,
  PharmacySale,
} from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-overview',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pharmacy-overview.component.html',
  styleUrls: ['./pharmacy-overview.component.scss'],
})
export class PharmacyOverviewComponent {
  private readonly pharmacyService = inject(PharmacyService);
  private readonly router = inject(Router);

  summary: PharmacyDashboardSummary | null = null;
  lowStockMedicines: PharmacyMedicine[] = [];
  pendingPrescriptions: PharmacyPendingPrescription[] = [];
  recentDispenses: PharmacyDispense[] = [];
  recentSales: PharmacySale[] = [];
  recentReturns: PharmacyReturn[] = [];

  constructor() {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.pharmacyService.getDashboardSummary().subscribe((summary) => (this.summary = summary));
    this.pharmacyService.listMedicines({ page: 1, page_size: 8, low_stock: true }).subscribe((response) => (this.lowStockMedicines = response.items));
    this.pharmacyService.listPendingPrescriptions().subscribe((items) => (this.pendingPrescriptions = items.slice(0, 8)));
    this.pharmacyService.list().subscribe((items) => (this.recentDispenses = items.slice(0, 6)));
    this.pharmacyService.listSales({ page: 1, page_size: 6 }).subscribe((response) => (this.recentSales = response.items));
    this.pharmacyService.listReturns({ page: 1, page_size: 6 }).subscribe((response) => (this.recentReturns = response.items));
  }

  open(path: string, queryParams: Record<string, string | number | null | undefined> = {}): void {
    void this.router.navigate([path], { queryParams });
  }

  get pharmacyKpis(): Array<{ label: string; value: string | number; detail: string }> {
    if (!this.summary) return [];
    return [
      { label: 'Sales', value: this.summary.total_sales, detail: `${this.recentSales.length} recent transactions` },
      { label: 'Low Stock', value: this.summary.low_stock_medicines, detail: 'Items below reorder level' },
      { label: 'Pending Rx', value: this.pendingPrescriptions.length, detail: 'Ready for dispense review' },
      { label: 'Catalog', value: this.summary.total_medicines, detail: `${this.summary.total_customers} customers recorded` },
    ];
  }

  get pharmacyAlerts(): Array<{ label: string; detail: string; value: number; route: string; tone: string }> {
    return [
      {
        label: 'Low-stock medicines',
        detail: 'Create purchase orders before stockout',
        value: this.lowStockMedicines.length,
        route: '/pharmacy/medicines',
        tone: this.lowStockMedicines.length ? 'warning' : 'good',
      },
      {
        label: 'Prescription queue',
        detail: 'Dispense pending clinical orders',
        value: this.pendingPrescriptions.length,
        route: '/pharmacy/dispense',
        tone: this.pendingPrescriptions.length ? 'warning' : 'good',
      },
    ];
  }

  formatCurrency(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2 }).format(Number(value ?? 0));
  }
}
