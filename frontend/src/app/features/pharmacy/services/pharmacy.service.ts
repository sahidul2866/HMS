import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  CompanyPayload,
  CustomerPayload,
  DispensePayload,
  InvestigationPayload,
  InvestigationSettingPayload,
  MasterPayload,
  MedicinePayload,
  PaginatedResponse,
  PharmacyCompany,
  PharmacyCustomer,
  PharmacyDashboardSummary,
  PharmacyDispense,
  PharmacyGeneric,
  PharmacyInvestigation,
  PharmacyInvestigationDraft,
  PharmacyInvestigationSetting,
  PharmacyMedicine,
  PharmacyMedicineType,
  PharmacyPendingPrescription,
  PharmacyPurchase,
  PharmacyReturn,
  PharmacyReturnPayload,
  PharmacySale,
  PharmacySalesDraft,
  PharmacyStockMovement,
  PharmacySummary,
  PurchasePayload,
  ReturnPayload,
  SalePayload,
} from '../models/pharmacy.models';

@Injectable({ providedIn: 'root' })
export class PharmacyService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getSummary(): Observable<PharmacySummary> {
    return this.cache.get('pharmacy:summary', () => this.http.get<PharmacySummary>(this.url('/pharmacy/summary')));
  }

  getDashboardSummary(): Observable<PharmacyDashboardSummary> {
    return this.cache.get('pharmacy:dashboard-summary', () => this.http.get<PharmacyDashboardSummary>(this.url('/pharmacy/dashboard-summary')));
  }

  list(): Observable<PharmacyDispense[]> {
    return this.cache.get('pharmacy:dispenses', () => this.http.get<PharmacyDispense[]>(this.url('/pharmacy/dispenses')));
  }

  listPendingPrescriptions(): Observable<PharmacyPendingPrescription[]> {
    return this.cache.get('pharmacy:pending-prescriptions', () => this.http.get<PharmacyPendingPrescription[]>(this.url('/pharmacy/opd-prescriptions')));
  }

  dispense(payload: DispensePayload): Observable<PharmacyDispense> {
    return this.http.post<PharmacyDispense>(this.url('/pharmacy/dispense'), payload).pipe(tap(() => this.clearCache()));
  }

  returnDispense(dispenseId: string, payload: PharmacyReturnPayload): Observable<PharmacyDispense> {
    return this.http.post<PharmacyDispense>(this.url(`/pharmacy/dispenses/${dispenseId}/return`), payload).pipe(tap(() => this.clearCache()));
  }

  listMedicineTypes(params: { page?: number; page_size?: number; q?: string } = {}): Observable<PaginatedResponse<PharmacyMedicineType>> {
    const query = this.toQuery(params);
    return this.cache.getPersistent(`pharmacy:medicine-types:${query}`, () => this.http.get<PaginatedResponse<PharmacyMedicineType>>(this.url(`/pharmacy/medicine-types${query}`)));
  }

  createMedicineType(payload: MasterPayload): Observable<PharmacyMedicineType> {
    return this.http.post<PharmacyMedicineType>(this.url('/pharmacy/medicine-types'), payload).pipe(tap(() => this.clearCache()));
  }

  updateMedicineType(id: string, payload: MasterPayload): Observable<PharmacyMedicineType> {
    return this.http.put<PharmacyMedicineType>(this.url(`/pharmacy/medicine-types/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteMedicineType(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/medicine-types/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listGenerics(params: { page?: number; page_size?: number; q?: string } = {}): Observable<PaginatedResponse<PharmacyGeneric>> {
    const query = this.toQuery(params);
    return this.cache.getPersistent(`pharmacy:generics:${query}`, () => this.http.get<PaginatedResponse<PharmacyGeneric>>(this.url(`/pharmacy/generics${query}`)));
  }

  createGeneric(payload: MasterPayload): Observable<PharmacyGeneric> {
    return this.http.post<PharmacyGeneric>(this.url('/pharmacy/generics'), payload).pipe(tap(() => this.clearCache()));
  }

  updateGeneric(id: string, payload: MasterPayload): Observable<PharmacyGeneric> {
    return this.http.put<PharmacyGeneric>(this.url(`/pharmacy/generics/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteGeneric(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/generics/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listCompanies(params: { page?: number; page_size?: number; q?: string } = {}): Observable<PaginatedResponse<PharmacyCompany>> {
    const query = this.toQuery(params);
    return this.cache.getPersistent(`pharmacy:companies:${query}`, () => this.http.get<PaginatedResponse<PharmacyCompany>>(this.url(`/pharmacy/companies${query}`)));
  }

  createCompany(payload: CompanyPayload): Observable<PharmacyCompany> {
    return this.http.post<PharmacyCompany>(this.url('/pharmacy/companies'), payload).pipe(tap(() => this.clearCache()));
  }

  updateCompany(id: string, payload: CompanyPayload): Observable<PharmacyCompany> {
    return this.http.put<PharmacyCompany>(this.url(`/pharmacy/companies/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteCompany(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/companies/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listCustomers(params: { page?: number; page_size?: number; q?: string } = {}): Observable<PaginatedResponse<PharmacyCustomer>> {
    const query = this.toQuery(params);
    return this.cache.get(`pharmacy:customers:${query}`, () => this.http.get<PaginatedResponse<PharmacyCustomer>>(this.url(`/pharmacy/customers${query}`)));
  }

  createCustomer(payload: CustomerPayload): Observable<PharmacyCustomer> {
    return this.http.post<PharmacyCustomer>(this.url('/pharmacy/customers'), payload).pipe(tap(() => this.clearCache()));
  }

  updateCustomer(id: string, payload: CustomerPayload): Observable<PharmacyCustomer> {
    return this.http.put<PharmacyCustomer>(this.url(`/pharmacy/customers/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteCustomer(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/customers/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listMedicines(params: Record<string, string | number | boolean | undefined> = {}): Observable<PaginatedResponse<PharmacyMedicine>> {
    const query = this.toQuery(params);
    return this.cache.getPersistent(`pharmacy:medicines:${query}`, () => this.http.get<PaginatedResponse<PharmacyMedicine>>(this.url(`/pharmacy/medicines${query}`)));
  }

  getMedicine(id: string): Observable<PharmacyMedicine> {
    return this.cache.get(`pharmacy:medicine:${id}`, () => this.http.get<PharmacyMedicine>(this.url(`/pharmacy/medicines/${id}`)));
  }

  createMedicine(payload: MedicinePayload): Observable<PharmacyMedicine> {
    return this.http.post<PharmacyMedicine>(this.url('/pharmacy/medicines'), payload).pipe(tap(() => this.clearCache()));
  }

  updateMedicine(id: string, payload: MedicinePayload): Observable<PharmacyMedicine> {
    return this.http.put<PharmacyMedicine>(this.url(`/pharmacy/medicines/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteMedicine(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/medicines/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listPurchases(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<PharmacyPurchase>> {
    const query = this.toQuery(params);
    return this.cache.get(`pharmacy:purchases:${query}`, () => this.http.get<PaginatedResponse<PharmacyPurchase>>(this.url(`/pharmacy/purchases${query}`)));
  }

  getPurchase(id: string): Observable<PharmacyPurchase> {
    return this.cache.get(`pharmacy:purchase:${id}`, () => this.http.get<PharmacyPurchase>(this.url(`/pharmacy/purchases/${id}`)));
  }

  createPurchase(payload: PurchasePayload): Observable<PharmacyPurchase> {
    return this.http.post<PharmacyPurchase>(this.url('/pharmacy/purchases'), payload).pipe(tap(() => this.clearCache()));
  }

  updatePurchase(id: string, payload: PurchasePayload): Observable<PharmacyPurchase> {
    return this.http.put<PharmacyPurchase>(this.url(`/pharmacy/purchases/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deletePurchase(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/purchases/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listSales(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<PharmacySale>> {
    const query = this.toQuery(params);
    return this.cache.get(`pharmacy:sales:${query}`, () => this.http.get<PaginatedResponse<PharmacySale>>(this.url(`/pharmacy/sales${query}`)));
  }

  getSale(id: string): Observable<PharmacySale> {
    return this.cache.get(`pharmacy:sale:${id}`, () => this.http.get<PharmacySale>(this.url(`/pharmacy/sales/${id}`)));
  }

  getSaleDraftFromVisit(visitId: string): Observable<PharmacySalesDraft> {
    return this.cache.get(`pharmacy:sale-draft:${visitId}`, () => this.http.get<PharmacySalesDraft>(this.url(`/pharmacy/sales-drafts/opd-visit/${visitId}`)));
  }

  createSale(payload: SalePayload): Observable<PharmacySale> {
    return this.http.post<PharmacySale>(this.url('/pharmacy/sales'), payload).pipe(tap(() => this.clearCache()));
  }

  updateSale(id: string, payload: SalePayload): Observable<PharmacySale> {
    return this.http.put<PharmacySale>(this.url(`/pharmacy/sales/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteSale(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/sales/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listReturns(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<PharmacyReturn>> {
    const query = this.toQuery(params);
    return this.cache.get(`pharmacy:returns:${query}`, () => this.http.get<PaginatedResponse<PharmacyReturn>>(this.url(`/pharmacy/returns${query}`)));
  }

  getReturn(id: string): Observable<PharmacyReturn> {
    return this.cache.get(`pharmacy:return:${id}`, () => this.http.get<PharmacyReturn>(this.url(`/pharmacy/returns/${id}`)));
  }

  createReturn(payload: ReturnPayload): Observable<PharmacyReturn> {
    return this.http.post<PharmacyReturn>(this.url('/pharmacy/returns'), payload).pipe(tap(() => this.clearCache()));
  }

  updateReturn(id: string, payload: ReturnPayload): Observable<PharmacyReturn> {
    return this.http.put<PharmacyReturn>(this.url(`/pharmacy/returns/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteReturn(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/pharmacy/returns/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listStockMovements(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<PharmacyStockMovement>> {
    const query = this.toQuery(params);
    return this.cache.get(`pharmacy:stock-movements:${query}`, () => this.http.get<PaginatedResponse<PharmacyStockMovement>>(this.url(`/pharmacy/stock-movements${query}`)));
  }

  listInvestigationSettings(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<PharmacyInvestigationSetting>> {
    const query = this.toQuery(params);
    return this.cache.getPersistent(`diagnostics:settings:${query}`, () => this.http.get<PaginatedResponse<PharmacyInvestigationSetting>>(this.url(`/diagnostics/settings${query}`)));
  }

  createInvestigationSetting(payload: InvestigationSettingPayload): Observable<PharmacyInvestigationSetting> {
    return this.http.post<PharmacyInvestigationSetting>(this.url('/diagnostics/settings'), payload).pipe(tap(() => this.clearCache()));
  }

  updateInvestigationSetting(id: string, payload: InvestigationSettingPayload): Observable<PharmacyInvestigationSetting> {
    return this.http.put<PharmacyInvestigationSetting>(this.url(`/diagnostics/settings/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteInvestigationSetting(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/diagnostics/settings/${id}`)).pipe(tap(() => this.clearCache()));
  }

  listInvestigations(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<PharmacyInvestigation>> {
    const query = this.toQuery(params);
    return this.cache.get(`diagnostics:orders:${query}`, () => this.http.get<PaginatedResponse<PharmacyInvestigation>>(this.url(`/diagnostics/orders${query}`)));
  }

  getInvestigation(id: string): Observable<PharmacyInvestigation> {
    return this.cache.get(`diagnostics:order:${id}`, () => this.http.get<PharmacyInvestigation>(this.url(`/diagnostics/orders/${id}`)));
  }

  getInvestigationDraftFromVisit(visitId: string): Observable<PharmacyInvestigationDraft> {
    return this.cache.get(`diagnostics:draft:${visitId}`, () => this.http.get<PharmacyInvestigationDraft>(this.url(`/diagnostics/drafts/opd-visit/${visitId}`)));
  }

  createInvestigation(payload: InvestigationPayload): Observable<PharmacyInvestigation> {
    return this.http.post<PharmacyInvestigation>(this.url('/diagnostics/orders'), payload).pipe(tap(() => this.clearCache()));
  }

  updateInvestigation(id: string, payload: InvestigationPayload): Observable<PharmacyInvestigation> {
    return this.http.put<PharmacyInvestigation>(this.url(`/diagnostics/orders/${id}`), payload).pipe(tap(() => this.clearCache()));
  }

  deleteInvestigation(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/diagnostics/orders/${id}`)).pipe(tap(() => this.clearCache()));
  }

  private toQuery(params: Record<string, string | number | boolean | undefined>): string {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    }
    const query = searchParams.toString();
    return query ? `?${query}` : '';
  }

  clearCache(): void {
    this.cache.clearPrefix('pharmacy:');
    this.cache.clearPrefix('diagnostics:');
    this.cache.clearPrefix('billing:');
    this.cache.clearPrefix('laboratory:');
    this.cache.clearPrefix('radiology:');
  }
}
