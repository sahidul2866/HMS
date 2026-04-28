import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  BillingInvoice,
  BillingInvoiceFilters,
  BillingInvoiceListItem,
  BillingInvoicePreview,
  BillingDraft,
  BillingReferralSummary,
  BillingSummary,
  BillingInvoiceVoidPayload,
  BillingPaymentPayload,
  BillingRefundPayload,
  BillingInvoiceItemPayload,
  BillingSettings,
  BillingService,
  CreateBillingInvoicePayload,
  CreateBillingServicePayload,
  UpdateBillingServiceControlsPayload,
} from '../models/billing.models';

@Injectable({ providedIn: 'root' })
export class BillingServiceApi extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  listServices(): Observable<BillingService[]> {
    return this.cache.getPersistent('billing:services', () => this.http.get<BillingService[]>(this.url('/billing/services')));
  }

  getSettings(): Observable<BillingSettings> {
    return this.cache.getPersistent('billing:settings', () => this.http.get<BillingSettings>(this.url('/billing/settings')));
  }

  updateSettings(payload: {
    max_item_discount_percentage: number;
    max_item_discount_amount?: number | null;
    max_invoice_discount_percentage: number;
    max_invoice_discount_amount?: number | null;
    default_referral_percentage: number;
  }): Observable<BillingSettings> {
    return this.http.patch<BillingSettings>(this.url('/billing/settings'), payload).pipe(tap(() => this.clearSettingsCache()));
  }

  createService(payload: CreateBillingServicePayload): Observable<BillingService> {
    return this.http.post<BillingService>(this.url('/billing/services'), payload).pipe(tap(() => this.clearServicesCache()));
  }

  updateServiceControls(id: string, payload: UpdateBillingServiceControlsPayload): Observable<BillingService> {
    return this.http.patch<BillingService>(this.url(`/billing/services/${id}/controls`), payload).pipe(tap(() => this.clearServicesCache()));
  }

  listInvoices(filters: BillingInvoiceFilters = {}): Observable<BillingInvoiceListItem[]> {
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.internal_referral_user_id) params.set('internal_referral_user_id', filters.internal_referral_user_id);
    if (filters.status) params.set('status', filters.status);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    const query = params.toString();
    return this.cache.get(`billing:invoices:${query}`, () => this.http.get<BillingInvoiceListItem[]>(this.url(`/billing/invoices${query ? `?${query}` : ''}`)));
  }

  getInvoice(invoiceId: string): Observable<BillingInvoice> {
    return this.cache.get(`billing:invoice:${invoiceId}`, () => this.http.get<BillingInvoice>(this.url(`/billing/invoices/${invoiceId}`)));
  }

  previewInvoice(discount_percentage: number, items: BillingInvoiceItemPayload[]): Observable<BillingInvoicePreview> {
    return this.http.post<BillingInvoicePreview>(this.url('/billing/invoices/preview'), { discount_percentage, items });
  }

  getOpdDraft(visitId: string): Observable<BillingDraft> {
    return this.cache.get(`billing:draft:opd:${visitId}`, () => this.http.get<BillingDraft>(this.url(`/billing/drafts/opd-visit/${visitId}`)));
  }

  getIpdDraft(admissionId: string, stage: 'interim' | 'final'): Observable<BillingDraft> {
    return this.cache.get(`billing:draft:ipd:${admissionId}:${stage}`, () => this.http.get<BillingDraft>(this.url(`/billing/drafts/ipd-admission/${admissionId}?stage=${encodeURIComponent(stage)}`)));
  }

  createInvoice(payload: CreateBillingInvoicePayload): Observable<BillingInvoice> {
    return this.http.post<BillingInvoice>(this.url('/billing/invoices'), payload).pipe(tap(() => this.clearInvoiceCache()));
  }

  voidInvoice(invoiceId: string, payload: BillingInvoiceVoidPayload): Observable<BillingInvoice> {
    return this.http.post<BillingInvoice>(this.url(`/billing/invoices/${invoiceId}/void`), payload).pipe(tap(() => this.clearInvoiceCache(invoiceId)));
  }

  collectPayment(invoiceId: string, payload: BillingPaymentPayload): Observable<BillingInvoice> {
    return this.http.post<BillingInvoice>(this.url(`/billing/invoices/${invoiceId}/payments`), payload).pipe(tap(() => this.clearInvoiceCache(invoiceId)));
  }

  createRefund(invoiceId: string, payload: BillingRefundPayload): Observable<BillingInvoice> {
    return this.http.post<BillingInvoice>(this.url(`/billing/invoices/${invoiceId}/refunds`), payload).pipe(tap(() => this.clearInvoiceCache(invoiceId)));
  }

  getSummary(filters: BillingInvoiceFilters = {}): Observable<BillingSummary> {
    const params = new URLSearchParams();
    if (filters.internal_referral_user_id) params.set('internal_referral_user_id', filters.internal_referral_user_id);
    if (filters.status) params.set('status', filters.status);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    const query = params.toString();
    return this.cache.get(`billing:summary:${query}`, () => this.http.get<BillingSummary>(this.url(`/billing/reports/summary${query ? `?${query}` : ''}`)));
  }

  getReferralSummary(filters: BillingInvoiceFilters = {}): Observable<BillingReferralSummary[]> {
    const params = new URLSearchParams();
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    const query = params.toString();
    return this.cache.get(`billing:referrals:${query}`, () => this.http.get<BillingReferralSummary[]>(this.url(`/billing/reports/referrals${query ? `?${query}` : ''}`)));
  }

  clearServicesCache(): void {
    this.cache.clear('billing:services');
  }

  clearSettingsCache(): void {
    this.cache.clear('billing:settings');
  }

  clearInvoiceCache(invoiceId?: string): void {
    this.cache.clearPrefix('billing:invoices:');
    this.cache.clearPrefix('billing:summary:');
    this.cache.clearPrefix('billing:referrals:');
    this.cache.clearPrefix('diagnostics:orders:');
    this.cache.clearPrefix('laboratory:');
    this.cache.clearPrefix('radiology:');
    this.cache.clearPrefix('opd:');
    if (invoiceId) {
      this.cache.clear(`billing:invoice:${invoiceId}`);
    } else {
      this.cache.clearPrefix('billing:invoice:');
    }
  }
}
