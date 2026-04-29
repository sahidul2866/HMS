import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import {
  InventoryDashboardSummary,
  InventoryItem,
  InventoryReport,
  PaginatedResponse,
  PurchaseRequest,
  Reagent,
  Supplier,
} from '../models/inventory.models';

@Injectable({ providedIn: 'root' })
export class InventoryService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

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

  clear(): void {
    this.cache.clearPrefix('inventory:');
    this.cache.clearPrefix('dashboard:');
  }
}
