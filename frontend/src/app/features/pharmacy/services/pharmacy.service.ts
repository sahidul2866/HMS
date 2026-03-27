import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  DispensePayload,
  PharmacyDispense,
  PharmacyPendingPrescription,
  PharmacyReturnPayload,
  PharmacySummary,
} from '../models/pharmacy.models';

@Injectable({ providedIn: 'root' })
export class PharmacyService extends ApiBaseService {
  getSummary(): Observable<PharmacySummary> {
    return this.http.get<PharmacySummary>(this.url('/pharmacy/summary'));
  }

  list(): Observable<PharmacyDispense[]> {
    return this.http.get<PharmacyDispense[]>(this.url('/pharmacy/dispenses'));
  }

  listPendingPrescriptions(): Observable<PharmacyPendingPrescription[]> {
    return this.http.get<PharmacyPendingPrescription[]>(this.url('/pharmacy/opd-prescriptions'));
  }

  dispense(payload: DispensePayload): Observable<PharmacyDispense> {
    return this.http.post<PharmacyDispense>(this.url('/pharmacy/dispense'), payload);
  }

  returnDispense(dispenseId: string, payload: PharmacyReturnPayload): Observable<PharmacyDispense> {
    return this.http.post<PharmacyDispense>(this.url(`/pharmacy/dispenses/${dispenseId}/return`), payload);
  }
}
