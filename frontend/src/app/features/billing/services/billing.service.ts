import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  BillingInvoice,
  BillingInvoiceFilters,
  BillingInvoiceListItem,
  BillingInvoicePreview,
  BillingReferralSummary,
  BillingSummary,
  BillingInvoiceVoidPayload,
  BillingInvoiceItemPayload,
  BillingService,
  CreateReferredDoctorPayload,
  CreateBillingInvoicePayload,
  CreateBillingServicePayload,
  ReferredDoctor,
} from '../models/billing.models';

@Injectable({ providedIn: 'root' })
export class BillingServiceApi extends ApiBaseService {
  listServices(): Observable<BillingService[]> {
    return this.http.get<BillingService[]>(this.url('/billing/services'));
  }

  createService(payload: CreateBillingServicePayload): Observable<BillingService> {
    return this.http.post<BillingService>(this.url('/billing/services'), payload);
  }

  listDoctors(): Observable<ReferredDoctor[]> {
    return this.http.get<ReferredDoctor[]>(this.url('/billing/doctors'));
  }

  createDoctor(payload: CreateReferredDoctorPayload): Observable<ReferredDoctor> {
    return this.http.post<ReferredDoctor>(this.url('/billing/doctors'), payload);
  }

  listInvoices(filters: BillingInvoiceFilters = {}): Observable<BillingInvoiceListItem[]> {
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.referred_doctor_id) params.set('referred_doctor_id', filters.referred_doctor_id);
    if (filters.status) params.set('status', filters.status);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    const query = params.toString();
    return this.http.get<BillingInvoiceListItem[]>(this.url(`/billing/invoices${query ? `?${query}` : ''}`));
  }

  getInvoice(invoiceId: string): Observable<BillingInvoice> {
    return this.http.get<BillingInvoice>(this.url(`/billing/invoices/${invoiceId}`));
  }

  previewInvoice(discount_percentage: number, items: BillingInvoiceItemPayload[]): Observable<BillingInvoicePreview> {
    return this.http.post<BillingInvoicePreview>(this.url('/billing/invoices/preview'), { discount_percentage, items });
  }

  createInvoice(payload: CreateBillingInvoicePayload): Observable<BillingInvoice> {
    return this.http.post<BillingInvoice>(this.url('/billing/invoices'), payload);
  }

  voidInvoice(invoiceId: string, payload: BillingInvoiceVoidPayload): Observable<BillingInvoice> {
    return this.http.post<BillingInvoice>(this.url(`/billing/invoices/${invoiceId}/void`), payload);
  }

  getSummary(filters: BillingInvoiceFilters = {}): Observable<BillingSummary> {
    const params = new URLSearchParams();
    if (filters.referred_doctor_id) params.set('referred_doctor_id', filters.referred_doctor_id);
    if (filters.status) params.set('status', filters.status);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    const query = params.toString();
    return this.http.get<BillingSummary>(this.url(`/billing/reports/summary${query ? `?${query}` : ''}`));
  }

  getReferralSummary(filters: BillingInvoiceFilters = {}): Observable<BillingReferralSummary[]> {
    const params = new URLSearchParams();
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    const query = params.toString();
    return this.http.get<BillingReferralSummary[]>(this.url(`/billing/reports/referrals${query ? `?${query}` : ''}`));
  }
}
