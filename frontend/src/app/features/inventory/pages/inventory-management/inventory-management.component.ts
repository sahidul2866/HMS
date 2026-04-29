import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import {
  InventoryDashboardSummary,
  InventoryItem,
  InventoryReport,
  PurchaseRequest,
  Reagent,
  Supplier,
} from '../../models/inventory.models';
import { InventoryService } from '../../services/inventory.service';

type InventoryTab = 'dashboard' | 'items' | 'reagents' | 'requests' | 'reports';

@Component({
  selector: 'app-inventory-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inventory-management.component.html',
  styleUrls: ['./inventory-management.component.scss'],
})
export class InventoryManagementComponent {
  private readonly inventoryService = inject(InventoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly tab = signal<InventoryTab>('dashboard');
  readonly tabs: { key: InventoryTab; label: string; route: string }[] = [
    { key: 'dashboard', label: 'Overview', route: '/inventory' },
    { key: 'items', label: 'Items', route: '/inventory/items' },
    { key: 'reagents', label: 'Reagents', route: '/inventory/reagents' },
    { key: 'requests', label: 'Requests', route: '/inventory/requests' },
    { key: 'reports', label: 'Reports', route: '/inventory/reports' },
  ];

  loading = false;
  error = '';
  query = '';
  lowStockOnly = false;
  dashboard: InventoryDashboardSummary | null = null;
  report: InventoryReport | null = null;
  items: InventoryItem[] = [];
  suppliers: Supplier[] = [];
  reagents: Reagent[] = [];
  requests: PurchaseRequest[] = [];

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['inventoryTab'] as InventoryTab) || 'dashboard');
      this.load();
    });
  }

  load(): void {
    this.error = '';
    this.loading = true;
    this.inventoryService.dashboard().subscribe({
      next: (summary) => (this.dashboard = summary),
      error: () => (this.error = 'Inventory summary could not be loaded.'),
    });
    this.inventoryService.reports().subscribe((report) => (this.report = report));
    this.inventoryService.listItems(this.query, this.lowStockOnly).subscribe({
      next: (response) => {
        this.items = response.items;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Inventory item list could not be loaded.';
      },
    });
    this.inventoryService.listSuppliers().subscribe((response) => (this.suppliers = response.items));
    this.inventoryService.listReagents(this.query).subscribe((response) => (this.reagents = response.items));
    this.inventoryService.listPurchaseRequests().subscribe((response) => (this.requests = response.items));
  }

  openTab(route: string): void {
    this.router.navigateByUrl(route);
  }

  num(value: string | number | null | undefined): number {
    return Number(value || 0);
  }

  formatMoney(value: string | number | null | undefined): string {
    return `BDT ${this.num(value).toLocaleString('en-BD', { maximumFractionDigits: 0 })}`;
  }

  statusClass(status: string | null | undefined): string {
    const value = (status || '').toLowerCase();
    if (['approved', 'active', 'ordered', 'in_use'].includes(value)) return 'badge good';
    if (['urgent', 'critical', 'requested', 'pending'].includes(value)) return 'badge warn';
    if (['rejected', 'expired', 'closed'].includes(value)) return 'badge danger';
    return 'badge info';
  }

  stockClass(item: InventoryItem): string {
    if (this.num(item.stock_quantity) <= 0) return 'danger-row';
    if (this.num(item.stock_quantity) <= this.num(item.reorder_level)) return 'warn-row';
    return '';
  }

  categoryEntries(): { label: string; value: number }[] {
    return Object.entries(this.dashboard?.category_counts || {}).map(([label, value]) => ({ label, value }));
  }

  maxCategory(): number {
    return Math.max(1, ...this.categoryEntries().map((item) => item.value));
  }
}
