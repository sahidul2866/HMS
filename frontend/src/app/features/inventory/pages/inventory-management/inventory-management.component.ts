import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import {
  InventoryDashboardSummary,
  InventoryItem,
  InventoryReport,
  InventoryRequisition,
  InventoryStore,
  InventoryStoreBalance,
  PurchaseRequest,
  Reagent,
  StockAdjustment,
  StockIssue,
  StockReceiving,
  StockTransfer,
  Supplier,
} from '../../models/inventory.models';
import { InventoryService } from '../../services/inventory.service';

type InventoryTab = 'dashboard' | 'items' | 'stock' | 'stores' | 'requisitions' | 'transfers' | 'receive' | 'issue' | 'adjustments' | 'suppliers' | 'reagents' | 'requests' | 'reports';

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

  readonly tab = signal<InventoryTab>('dashboard');

  loading = false;
  error = '';
  query = '';
  lowStockOnly = false;
  storeFilter = '';
  statusFilter = '';
  dashboard: InventoryDashboardSummary | null = null;
  report: InventoryReport | null = null;
  items: InventoryItem[] = [];
  stores: InventoryStore[] = [];
  stock: InventoryStoreBalance[] = [];
  suppliers: Supplier[] = [];
  reagents: Reagent[] = [];
  requests: PurchaseRequest[] = [];
  requisitions: InventoryRequisition[] = [];
  transfers: StockTransfer[] = [];
  receivings: StockReceiving[] = [];
  issues: StockIssue[] = [];
  adjustments: StockAdjustment[] = [];

  storeForm = {
    code: '',
    name: '',
    store_type: 'sub_store',
    department_name: '',
    location: '',
    is_active: true,
    allow_sub_store_transfers: true,
  };

  movementForm = {
    item_id: '',
    store_id: '',
    source_store_id: '',
    destination_store_id: '',
    supplier_id: '',
    quantity: 1,
    unit_cost: 0,
    batch_no: '',
    expiry_date: '',
    department: '',
    purpose: '',
    reason: '',
    note: '',
    priority: 'normal',
    required_date: '',
  };

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
    this.inventoryService.listStores().subscribe((response) => (this.stores = response.items));
    this.inventoryService.listStock({ q: this.query, store_id: this.storeFilter, stock_status: this.statusFilter }).subscribe((response) => (this.stock = response.items));
    this.inventoryService.listSuppliers().subscribe((response) => (this.suppliers = response.items));
    this.inventoryService.listReagents(this.query).subscribe((response) => (this.reagents = response.items));
    this.inventoryService.listPurchaseRequests().subscribe((response) => (this.requests = response.items));
    this.inventoryService.listRequisitions({ q: this.query, store_id: this.storeFilter, status: this.statusFilter }).subscribe((response) => (this.requisitions = response.items));
    this.inventoryService.listTransfers(this.query).subscribe((response) => (this.transfers = response.items));
    this.inventoryService.listReceivings(this.query).subscribe((response) => (this.receivings = response.items));
    this.inventoryService.listIssues(this.query).subscribe((response) => (this.issues = response.items));
    this.inventoryService.listAdjustments(this.query).subscribe((response) => (this.adjustments = response.items));
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

  storeValueEntries(): { label: string; value: number }[] {
    return Object.entries(this.dashboard?.store_stock_value || {}).map(([label, value]) => ({ label, value: this.num(value) }));
  }

  setQuickAction(action: 'receive' | 'issue' | 'transfer' | 'requisition' | 'adjustment'): void {
    const tabMap = {
      receive: 'receive',
      issue: 'issue',
      transfer: 'transfers',
      requisition: 'requisitions',
      adjustment: 'adjustments',
    } as const;
    this.tab.set(tabMap[action]);
  }

  saveStore(): void {
    if (!this.storeForm.code.trim() || !this.storeForm.name.trim()) return;
    this.inventoryService.saveStore(this.storeForm).subscribe({
      next: () => this.reloadAfterMutation(),
      error: () => (this.error = 'Store could not be saved.'),
    });
  }

  createReceiving(): void {
    if (!this.movementForm.item_id || !this.movementForm.store_id || this.movementForm.quantity <= 0) return;
    const quantity = Number(this.movementForm.quantity);
    const unitCost = Number(this.movementForm.unit_cost || 0);
    this.inventoryService.createReceiving({
      item_id: this.movementForm.item_id,
      store_id: this.movementForm.store_id,
      supplier_id: this.movementForm.supplier_id || null,
      invoice_number: null,
      received_date: this.today(),
      department: this.selectedStore(this.movementForm.store_id)?.department_name || null,
      batch_no: this.movementForm.batch_no || null,
      expiry_date: this.movementForm.expiry_date || null,
      quantity,
      unit_cost: unitCost,
      total_cost: quantity * unitCost,
      note: this.movementForm.note || null,
      location: this.selectedStore(this.movementForm.store_id)?.location || null,
    }).subscribe({ next: () => this.reloadAfterMutation(), error: () => (this.error = 'Stock could not be received.') });
  }

  createIssue(): void {
    if (!this.movementForm.item_id || !this.movementForm.store_id || this.movementForm.quantity <= 0) return;
    this.inventoryService.createIssue({
      item_id: this.movementForm.item_id,
      store_id: this.movementForm.store_id,
      department: this.movementForm.department || this.selectedStore(this.movementForm.store_id)?.department_name || null,
      requestor: null,
      purpose: this.movementForm.purpose || null,
      quantity: Number(this.movementForm.quantity),
      issue_date: this.today(),
      note: this.movementForm.note || null,
    }).subscribe({ next: () => this.reloadAfterMutation(), error: () => (this.error = 'Stock could not be issued.') });
  }

  createTransfer(): void {
    if (!this.movementForm.item_id || !this.movementForm.source_store_id || !this.movementForm.destination_store_id || this.movementForm.quantity <= 0) return;
    this.inventoryService.createTransfer({
      item_id: this.movementForm.item_id,
      source_store_id: this.movementForm.source_store_id,
      destination_store_id: this.movementForm.destination_store_id,
      quantity: Number(this.movementForm.quantity),
      requested_quantity: Number(this.movementForm.quantity),
      transfer_date: this.today(),
      status: 'received',
      note: this.movementForm.note || null,
    }).subscribe({ next: () => this.reloadAfterMutation(), error: () => (this.error = 'Stock could not be transferred.') });
  }

  createRequisition(): void {
    if (!this.movementForm.item_id || !this.movementForm.destination_store_id || this.movementForm.quantity <= 0) return;
    this.inventoryService.saveRequisition({
      item_id: this.movementForm.item_id,
      source_store_id: this.movementForm.source_store_id || this.mainStore()?.id || null,
      destination_store_id: this.movementForm.destination_store_id,
      department: this.selectedStore(this.movementForm.destination_store_id)?.department_name || null,
      requested_quantity: Number(this.movementForm.quantity),
      priority: this.movementForm.priority,
      required_date: this.movementForm.required_date || null,
      reason: this.movementForm.reason || null,
      status: 'requested',
      remarks: this.movementForm.note || null,
    }).subscribe({ next: () => this.reloadAfterMutation(), error: () => (this.error = 'Requisition could not be created.') });
  }

  createAdjustment(): void {
    if (!this.movementForm.item_id || !this.movementForm.store_id || this.movementForm.quantity <= 0) return;
    this.inventoryService.createAdjustment({
      item_id: this.movementForm.item_id,
      store_id: this.movementForm.store_id,
      adjustment_type: this.movementForm.reason === 'addition' ? 'addition' : 'deduction',
      quantity_change: Number(this.movementForm.quantity),
      reason: this.movementForm.reason || 'correction',
      note: this.movementForm.note || null,
      status: 'posted',
      created_at: this.today(),
    }).subscribe({ next: () => this.reloadAfterMutation(), error: () => (this.error = 'Adjustment could not be posted.') });
  }

  selectedStore(storeId: string): InventoryStore | undefined {
    return this.stores.find((store) => store.id === storeId);
  }

  mainStore(): InventoryStore | undefined {
    return this.stores.find((store) => store.store_type === 'main');
  }

  private today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private reloadAfterMutation(): void {
    this.inventoryService.clear();
    this.load();
  }
}
