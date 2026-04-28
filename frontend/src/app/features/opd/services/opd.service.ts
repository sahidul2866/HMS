import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
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
    return this.http.post<OPDVisit>(this.url('/opd/visits'), payload).pipe(tap(() => this.clearCache()));
  }

  updateVisit(visitId: string, payload: UpdateOPDVisitPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}`), payload).pipe(tap(() => this.clearCache()));
  }

  updateStatus(visitId: string, status: string): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/status`), { status }).pipe(tap(() => this.clearCache()));
  }

  updatePayment(visitId: string, payload: UpdateOPDPaymentPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/payment`), payload).pipe(tap(() => this.clearCache()));
  }

  updateConsultation(visitId: string, payload: UpdateOPDConsultationPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/consultation`), payload).pipe(tap(() => this.clearCache()));
  }

  createOrder(visitId: string, payload: CreateOPDVisitOrderPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url(`/opd/visits/${visitId}/orders`), payload).pipe(tap(() => this.clearCache()));
  }

  updateOrder(visitId: string, orderId: string, payload: UpdateOPDVisitOrderPayload): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/orders/${orderId}`), payload).pipe(tap(() => this.clearCache()));
  }

  convertToIPD(visitId: string, payload: ConvertOPDToIPDPayload): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url(`/opd/visits/${visitId}/convert-to-ipd`), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('opd:');
    this.cache.clearPrefix('ipd:');
    this.cache.clearPrefix('laboratory:');
    this.cache.clearPrefix('radiology:');
  }
}
