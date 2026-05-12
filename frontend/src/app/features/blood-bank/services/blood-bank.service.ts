import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import {
  BloodBankDashboard,
  BloodBankReport,
  BloodDonor,
  BloodDonorPayload,
  BloodRequest,
  BloodUnit,
  CollectionPayload,
  ComponentPayload,
  CrossmatchPayload,
  DiscardPayload,
  IssuePayload,
  PaginatedResponse,
  RequestPayload,
  ReturnPayload,
  ScreeningPayload,
  StorageLocation,
  TestPayload,
  TransfusionPayload,
} from '../models/blood-bank.models';

@Injectable({ providedIn: 'root' })
export class BloodBankService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  getDashboard(): Observable<BloodBankDashboard> {
    return this.cache.get('blood-bank:dashboard', () => this.http.get<BloodBankDashboard>(this.url('/blood-bank/dashboard')));
  }

  listDonors(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<BloodDonor>> {
    const query = this.toQuery(params);
    return this.cache.get(`blood-bank:donors:${query}`, () => this.http.get<PaginatedResponse<BloodDonor>>(this.url(`/blood-bank/donors${query}`)));
  }

  createDonor(payload: BloodDonorPayload): Observable<BloodDonor> {
    return this.http.post<BloodDonor>(this.url('/blood-bank/donors'), payload).pipe(tap(() => this.clearCache()));
  }

  screenDonor(payload: ScreeningPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/screenings'), payload).pipe(tap(() => this.clearCache()));
  }

  collectBlood(payload: CollectionPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/collections'), payload).pipe(tap(() => this.clearCache()));
  }

  listUnits(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<BloodUnit>> {
    const query = this.toQuery(params);
    return this.cache.get(`blood-bank:units:${query}`, () => this.http.get<PaginatedResponse<BloodUnit>>(this.url(`/blood-bank/units${query}`)));
  }

  updateTest(payload: TestPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/tests'), payload).pipe(tap(() => this.clearCache()));
  }

  prepareComponent(payload: ComponentPayload): Observable<BloodUnit> {
    return this.http.post<BloodUnit>(this.url('/blood-bank/components'), payload).pipe(tap(() => this.clearCache()));
  }

  listLocations(): Observable<StorageLocation[]> {
    return this.cache.get('blood-bank:locations', () => this.http.get<StorageLocation[]>(this.url('/blood-bank/locations')));
  }

  createLocation(payload: Partial<StorageLocation> & { code: string; name: string }): Observable<StorageLocation> {
    return this.http.post<StorageLocation>(this.url('/blood-bank/locations'), payload).pipe(tap(() => this.clearCache()));
  }

  moveUnit(unitId: string, storageLocationId: string, remarks = ''): Observable<BloodUnit> {
    return this.http.post<BloodUnit>(this.url(`/blood-bank/units/${unitId}/move`), { storage_location_id: storageLocationId, remarks }).pipe(tap(() => this.clearCache()));
  }

  listRequests(params: Record<string, string | number | undefined> = {}): Observable<PaginatedResponse<BloodRequest>> {
    const query = this.toQuery(params);
    return this.cache.get(`blood-bank:requests:${query}`, () => this.http.get<PaginatedResponse<BloodRequest>>(this.url(`/blood-bank/requests${query}`)));
  }

  createRequest(payload: RequestPayload): Observable<BloodRequest> {
    return this.http.post<BloodRequest>(this.url('/blood-bank/requests'), payload).pipe(tap(() => this.clearCache()));
  }

  crossmatch(payload: CrossmatchPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/crossmatches'), payload).pipe(tap(() => this.clearCache()));
  }

  issue(payload: IssuePayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/issues'), payload).pipe(tap(() => this.clearCache()));
  }

  updateTransfusion(payload: TransfusionPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/transfusions'), payload).pipe(tap(() => this.clearCache()));
  }

  returnUnit(payload: ReturnPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/returns'), payload).pipe(tap(() => this.clearCache()));
  }

  discard(payload: DiscardPayload): Observable<unknown> {
    return this.http.post(this.url('/blood-bank/discards'), payload).pipe(tap(() => this.clearCache()));
  }

  report(params: Record<string, string | undefined>): Observable<BloodBankReport> {
    const query = this.toQuery(params);
    return this.http.get<BloodBankReport>(this.url(`/blood-bank/reports${query}`));
  }

  clearCache(): void {
    this.cache.clearPrefix('blood-bank');
  }

  private toQuery(params: Record<string, string | number | undefined>): string {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') search.set(key, String(value));
    });
    const query = search.toString();
    return query ? `?${query}` : '';
  }
}
