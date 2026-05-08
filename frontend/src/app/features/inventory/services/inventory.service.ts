import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import {
  InventoryDashboardSummary,
  InventoryItem,
  InventoryReport,
  InventoryRequisition,
  InventoryStore,
  InventoryStoreBalance,
  PaginatedResponse,
  PurchaseRequest,
  Reagent,
  StockAdjustment,
  StockIssue,
  StockReceiving,
  StockTransfer,
  Supplier,
} from '../models/inventory.models';

@Injectable({ providedIn: 'root' })
export class InventoryService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  dashboard(): Observable<InventoryDashboardSummary> {
    return this.cache.get('inventory:dashboard', () => this.http.get<InventoryDashboardSummary>(this.url('/inventory/dashboard')));
  }

  reports(): Observable<InventoryReport> {
    return this.cache.get('inventory:reports', () => this.http.get<InventoryReport>(this.url('/inventory/reports')));
  }

  listItems(q = '', lowStock = false): Observable<PaginatedResponse<InventoryItem>> {
    const params = new URLSearchParams({ page: '1', page_size: '60' });
    if (q.trim()) params.set('q', q.trim());
    if (lowStock) params.set('low_stock', 'true');
    const query = params.toString();
    return this.cache.get(`inventory:items:${query}`, () => this.http.get<PaginatedResponse<InventoryItem>>(this.url(`/inventory/items?${query}`)));
  }

  listStores(q = '', includeInactive = false): Observable<PaginatedResponse<InventoryStore>> {
    const params = new URLSearchParams({ page: '1', page_size: '80' });
    if (q.trim()) params.set('q', q.trim());
    if (includeInactive) params.set('include_inactive', 'true');
    const query = params.toString();
    return this.cache.get(`inventory:stores:${query}`, () => this.http.get<PaginatedResponse<InventoryStore>>(this.url(`/inventory/stores?${query}`)));
  }

  saveStore(payload: Partial<InventoryStore> & { code: string; name: string; store_type: string }, storeId?: string): Observable<InventoryStore> {
    const request = storeId
      ? this.http.put<InventoryStore>(this.url(`/inventory/stores/${storeId}`), payload)
      : this.http.post<InventoryStore>(this.url('/inventory/stores'), payload);
    return request.pipe(
      tap((store) => {
        this.clear();
        this.publishInventoryEvent('data.updated', 'inventory_store', store.id, 'Inventory store list updated.');
      })
    );
  }

  listStock(filters: { q?: string; store_id?: string; item_id?: string; stock_status?: string } = {}): Observable<PaginatedResponse<InventoryStoreBalance>> {
    const params = new URLSearchParams({ page: '1', page_size: '120' });
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const query = params.toString();
    return this.cache.get(`inventory:stock:${query}`, () => this.http.get<PaginatedResponse<InventoryStoreBalance>>(this.url(`/inventory/stock?${query}`)));
  }

  listSuppliers(q = ''): Observable<PaginatedResponse<Supplier>> {
    const params = new URLSearchParams({ page: '1', page_size: '30' });
    if (q.trim()) params.set('q', q.trim());
    const query = params.toString();
    return this.cache.get(`inventory:suppliers:${query}`, () => this.http.get<PaginatedResponse<Supplier>>(this.url(`/inventory/suppliers?${query}`)));
  }

  listReagents(q = ''): Observable<PaginatedResponse<Reagent>> {
    const params = new URLSearchParams({ page: '1', page_size: '50' });
    if (q.trim()) params.set('q', q.trim());
    const query = params.toString();
    return this.cache.get(`inventory:reagents:${query}`, () => this.http.get<PaginatedResponse<Reagent>>(this.url(`/inventory/reagents?${query}`)));
  }

  listPurchaseRequests(): Observable<PaginatedResponse<PurchaseRequest>> {
    return this.cache.get(
      'inventory:purchase-requests',
      () => this.http.get<PaginatedResponse<PurchaseRequest>>(this.url('/inventory/purchase-requests?page=1&page_size=30')),
    );
  }

  listRequisitions(filters: { q?: string; store_id?: string; status?: string } = {}): Observable<PaginatedResponse<InventoryRequisition>> {
    const params = new URLSearchParams({ page: '1', page_size: '80' });
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const query = params.toString();
    return this.cache.get(`inventory:requisitions:${query}`, () => this.http.get<PaginatedResponse<InventoryRequisition>>(this.url(`/inventory/requisitions?${query}`)));
  }

  saveRequisition(payload: Record<string, unknown>, requisitionId?: string): Observable<InventoryRequisition> {
    const request = requisitionId
      ? this.http.put<InventoryRequisition>(this.url(`/inventory/requisitions/${requisitionId}`), payload)
      : this.http.post<InventoryRequisition>(this.url('/inventory/requisitions'), payload);
    return request.pipe(
      tap((requisition) => {
        this.clear();
        this.publishInventoryEvent('inventory.stock.updated', 'inventory_requisition', requisition.id, 'Inventory requisition updated.');
      })
    );
  }

  listTransfers(q = ''): Observable<PaginatedResponse<StockTransfer>> {
    const params = new URLSearchParams({ page: '1', page_size: '80' });
    if (q.trim()) params.set('q', q.trim());
    const query = params.toString();
    return this.cache.get(`inventory:transfers:${query}`, () => this.http.get<PaginatedResponse<StockTransfer>>(this.url(`/inventory/transfers?${query}`)));
  }

  createTransfer(payload: Record<string, unknown>): Observable<StockTransfer> {
    return this.http.post<StockTransfer>(this.url('/inventory/transfers'), payload).pipe(
      tap((transfer) => {
        this.clear();
        this.publishInventoryEvent('inventory.stock.updated', 'stock_transfer', transfer.id, 'Stock quantity changed.');
      })
    );
  }

  listReceivings(q = ''): Observable<PaginatedResponse<StockReceiving>> {
    const params = new URLSearchParams({ page: '1', page_size: '80' });
    if (q.trim()) params.set('q', q.trim());
    const query = params.toString();
    return this.cache.get(`inventory:receivings:${query}`, () => this.http.get<PaginatedResponse<StockReceiving>>(this.url(`/inventory/receivings?${query}`)));
  }

  createReceiving(payload: Record<string, unknown>): Observable<StockReceiving> {
    return this.http.post<StockReceiving>(this.url('/inventory/receivings'), payload).pipe(
      tap((receiving) => {
        this.clear();
        this.publishInventoryEvent('inventory.stock.updated', 'stock_receiving', receiving.id, 'Stock quantity changed.');
      })
    );
  }

  listIssues(q = ''): Observable<PaginatedResponse<StockIssue>> {
    const params = new URLSearchParams({ page: '1', page_size: '80' });
    if (q.trim()) params.set('q', q.trim());
    const query = params.toString();
    return this.cache.get(`inventory:issues:${query}`, () => this.http.get<PaginatedResponse<StockIssue>>(this.url(`/inventory/issues?${query}`)));
  }

  createIssue(payload: Record<string, unknown>): Observable<StockIssue> {
    return this.http.post<StockIssue>(this.url('/inventory/issues'), payload).pipe(
      tap((issue) => {
        this.clear();
        this.publishInventoryEvent('inventory.stock.updated', 'stock_issue', issue.id, 'Stock quantity changed.', issue.patient_id, issue.visit_id);
      })
    );
  }

  listAdjustments(q = ''): Observable<PaginatedResponse<StockAdjustment>> {
    const params = new URLSearchParams({ page: '1', page_size: '80' });
    if (q.trim()) params.set('q', q.trim());
    const query = params.toString();
    return this.cache.get(`inventory:adjustments:${query}`, () => this.http.get<PaginatedResponse<StockAdjustment>>(this.url(`/inventory/adjustments?${query}`)));
  }

  createAdjustment(payload: Record<string, unknown>): Observable<StockAdjustment> {
    return this.http.post<StockAdjustment>(this.url('/inventory/adjustments'), payload).pipe(
      tap((adjustment) => {
        this.clear();
        this.publishInventoryEvent('inventory.stock.updated', 'stock_adjustment', adjustment.id, 'Stock quantity changed.');
      })
    );
  }

  clear(): void {
    this.cache.clearPrefix('inventory:');
    this.cache.clearPrefix('dashboard:');
  }

  private publishInventoryEvent(
    name: 'inventory.stock.updated' | 'data.updated',
    entityType: string,
    entityId: string | null,
    message: string,
    patientId?: string | null,
    visitId?: string | null
  ): void {
    this.dataSync.publish({
      name,
      entityType,
      entityId,
      patientId,
      visitId,
      modules: ['inventory', 'pharmacy', 'billing', 'laboratory', 'radiology', 'opd', 'patients', 'dashboard'],
      cachePrefixes: ['inventory:', 'pharmacy:', 'billing:', 'laboratory:', 'radiology:', 'diagnostics:', 'opd:', 'patients:', 'dashboard:'],
      message,
    });
  }
}
