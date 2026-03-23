import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { IPDAdmission } from '../../ipd/models/ipd.models';
import { ConvertOPDToIPDPayload, CreateOPDVisitOrderPayload, CreateOPDVisitPayload, OPDSummary, OPDVisit } from '../models/opd.models';

@Injectable({ providedIn: 'root' })
export class OPDService extends ApiBaseService {
  listVisits(): Observable<OPDVisit[]> {
    return this.http.get<OPDVisit[]>(this.url('/opd/visits'));
  }

  getSummary(): Observable<OPDSummary> {
    return this.http.get<OPDSummary>(this.url('/opd/summary'));
  }

  createVisit(payload: CreateOPDVisitPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url('/opd/visits'), payload);
  }

  updateStatus(visitId: string, status: string): Observable<OPDVisit> {
    return this.http.put<OPDVisit>(this.url(`/opd/visits/${visitId}/status`), { status });
  }

  createOrder(visitId: string, payload: CreateOPDVisitOrderPayload): Observable<OPDVisit> {
    return this.http.post<OPDVisit>(this.url(`/opd/visits/${visitId}/orders`), payload);
  }

  convertToIPD(visitId: string, payload: ConvertOPDToIPDPayload): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url(`/opd/visits/${visitId}/convert-to-ipd`), payload);
  }
}
