import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { DispensePayload, PharmacyDispense, PharmacyPendingPrescription } from '../models/pharmacy.models';

@Injectable({ providedIn: 'root' })
export class PharmacyService extends ApiBaseService {
  list(): Observable<PharmacyDispense[]> {
    return this.http.get<PharmacyDispense[]>(this.url('/pharmacy/dispenses'));
  }

  listPendingPrescriptions(): Observable<PharmacyPendingPrescription[]> {
    return this.http.get<PharmacyPendingPrescription[]>(this.url('/pharmacy/opd-prescriptions'));
  }

  dispense(payload: DispensePayload): Observable<PharmacyDispense> {
    return this.http.post<PharmacyDispense>(this.url('/pharmacy/dispense'), payload);
  }
}
