import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import { IPDAdmission } from '../../ipd/models/ipd.models';
import {
  ConvertOPDToIPDPayload,
  CreateOPDVisitOrderPayload,
  CreateOPDVisitPayload,
  OPDSummary,
  OPDVisit,
  UpdateOPDConsultationPayload,
  UpdateOPDPaymentPayload,
  UpdateOPDVisitPayload,
  UpdateOPDVisitOrderPayload,
} from '../models/opd.models';

@Injectable({ providedIn: 'root' })
export class OPDService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  listVisits(doctorUserId?: string | null): Observable<OPDVisit[]> {
    const params = doctorUserId ? `?doctor_user_id=${encodeURIComponent(doctorUserId)}` : '';
    return this.cache.get(`opd:visits:${params}`, () => this.http.get<OPDVisit[]>(this.url(`/opd/visits${params}`)));
  }

  getVisit(visitId: string): Observable<OPDVisit> {
    return this.cache.get(`opd:visit:${visitId}`, () => this.http.get<OPDVisit>(this.url(`/opd/visits/${visitId}`)));
  }

  getPatientVisits(patientId: string): Observable<OPDVisit[]> {
    return this.cache.get(`opd:patient:${patientId}`, () => this.http.get<OPDVisit[]>(this.url(`/patients/${patientId}/opd-visits`)));
  }

  getSummary(doctorUserId?: string | null): Observable<OPDSummary> {
    const params = doctorUserId ? `?doctor_user_id=${encodeURIComponent(doctorUserId)}` : '';
    return this.cache.get(`opd:summary:${params}`, () => this.http.get<OPDSummary>(this.url(`/opd/summary${params}`)));
  }

  createVisit(payload: CreateOPDVisitPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url('/opd/visits'), payload).pipe(tap((visit) => this.publishVisitEvent('data.updated', visit, 'OPD visit created.')));
  }

  updateVisit(visitId: string, payload: UpdateOPDVisitPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}`), payload).pipe(tap((visit) => this.publishVisitEvent('data.updated', visit, 'OPD visit updated.')));
  }

  updateStatus(visitId: string, status: string): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/status`), { status }).pipe(tap((visit) => this.publishVisitEvent('data.updated', visit, 'OPD status updated.')));
  }

  updatePayment(visitId: string, payload: UpdateOPDPaymentPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/payment`), payload).pipe(tap((visit) => this.publishVisitEvent('billing.payment.received', visit, 'OPD payment status updated.')));
  }

  updateConsultation(visitId: string, payload: UpdateOPDConsultationPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/consultation`), payload).pipe(tap((visit) => this.publishVisitEvent('prescription.updated', visit, 'Prescription/consultation updated.')));
  }

  createOrder(visitId: string, payload: CreateOPDVisitOrderPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url(`/opd/visits/${visitId}/orders`), payload).pipe(tap((visit) => this.publishVisitEvent(payload.order_type === 'prescription' ? 'prescription.created' : 'lab.order.created', visit, payload.order_type === 'prescription' ? 'Prescription medicine added.' : 'Investigation/order added.')));
  }

  updateOrder(visitId: string, orderId: string, payload: UpdateOPDVisitOrderPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/orders/${orderId}`), payload).pipe(tap((visit) => this.publishVisitEvent('prescription.updated', visit, 'Prescription/order updated.')));
  }

  deleteOrder(visitId: string, orderId: string): Observable<OPDVisit> {
    return this.http.delete<OPDVisit>(this.url(`/opd/visits/${visitId}/orders/${orderId}`)).pipe(tap((visit) => this.publishVisitEvent('prescription.updated', visit, 'Prescription/order removed.')));
  }

  convertToIPD(visitId: string, payload: ConvertOPDToIPDPayload): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url(`/opd/visits/${visitId}/convert-to-ipd`), payload).pipe(tap((admission) => {
      this.clearCache();
      this.dataSync.publish({
        name: 'ipd.bed.assigned',
        entityType: 'ipd_admission',
        entityId: admission.id,
        patientId: admission.patient?.id,
        visitId,
        modules: ['ipd', 'opd', 'patients', 'billing', 'dashboard'],
        cachePrefixes: ['ipd:', 'opd:', 'patients:', 'billing:', 'dashboard:'],
        message: 'OPD visit converted to IPD.',
      });
    }));
  }

  clearCache(): void {
    this.cache.clearPrefix('opd:');
    this.cache.clearPrefix('ipd:');
    this.cache.clearPrefix('laboratory:');
    this.cache.clearPrefix('radiology:');
  }

  private publishVisitEvent(name: 'data.updated' | 'billing.payment.received' | 'prescription.created' | 'prescription.updated' | 'lab.order.created', visit: OPDVisit, message: string): void {
    this.clearCache();
    this.dataSync.publish({
      name,
      entityType: 'opd_visit',
      entityId: visit.id,
      patientId: visit.patient?.id,
      visitId: visit.id,
      modules: ['opd', 'patients', 'billing', 'pharmacy', 'laboratory', 'radiology', 'dashboard'],
      cachePrefixes: ['opd:', 'patients:', 'billing:', 'pharmacy:', 'laboratory:', 'radiology:', 'diagnostics:', 'dashboard:'],
      message,
    });
  }
}
