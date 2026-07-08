import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import {
  TransportDashboard,
  TransportDriver,
  TransportFuelLog,
  TransportMaintenance,
  TransportReport,
  TransportRequest,
  TransportSchedule,
  TransportSetting,
  TransportTrip,
  TransportVehicle,
} from '../models/transport.models';

@Injectable({ providedIn: 'root' })
export class TransportService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  dashboard(params: Record<string, string | number | null | undefined> = {}): Observable<TransportDashboard> {
    const query = this.query(params);
    return this.cache.get(`transport:dashboard:${query}`, () => this.http.get<TransportDashboard>(this.url(`/transport/dashboard${query}`)));
  }

  listVehicles(params: Record<string, string | undefined> = {}): Observable<TransportVehicle[]> {
    const query = this.query(params);
    return this.cache.get(`transport:vehicles:${query}`, () => this.http.get<TransportVehicle[]>(this.url(`/transport/vehicles${query}`)));
  }

  saveVehicle(payload: Partial<TransportVehicle> | Record<string, unknown>, id?: string): Observable<TransportVehicle> {
    const request = id ? this.http.put<TransportVehicle>(this.url(`/transport/vehicles/${id}`), payload) : this.http.post<TransportVehicle>(this.url('/transport/vehicles'), payload);
    return request.pipe(tap(() => this.publish()));
  }

  listDrivers(params: Record<string, string | undefined> = {}): Observable<TransportDriver[]> {
    const query = this.query(params);
    return this.cache.get(`transport:drivers:${query}`, () => this.http.get<TransportDriver[]>(this.url(`/transport/drivers${query}`)));
  }

  saveDriver(payload: Partial<TransportDriver> | Record<string, unknown>, id?: string): Observable<TransportDriver> {
    const request = id ? this.http.put<TransportDriver>(this.url(`/transport/drivers/${id}`), payload) : this.http.post<TransportDriver>(this.url('/transport/drivers'), payload);
    return request.pipe(tap(() => this.publish()));
  }

  listRequests(params: Record<string, string | undefined> = {}): Observable<TransportRequest[]> {
    const query = this.query(params);
    return this.cache.get(`transport:requests:${query}`, () => this.http.get<TransportRequest[]>(this.url(`/transport/requests${query}`)));
  }

  createRequest(payload: Partial<TransportRequest> | Record<string, unknown>, emergency = false): Observable<TransportRequest> {
    const path = emergency ? '/transport/requests/emergency' : '/transport/requests';
    return this.http.post<TransportRequest>(this.url(path), payload).pipe(tap(() => this.publish()));
  }

  dispatch(requestId: string, payload: Record<string, unknown>): Observable<TransportTrip> {
    return this.http.post<TransportTrip>(this.url(`/transport/requests/${requestId}/dispatch`), payload).pipe(tap(() => this.publish()));
  }

  listTrips(params: Record<string, string | undefined> = {}): Observable<TransportTrip[]> {
    const query = this.query(params);
    return this.cache.get(`transport:trips:${query}`, () => this.http.get<TransportTrip[]>(this.url(`/transport/trips${query}`)));
  }

  updateTripStatus(tripId: string, payload: Record<string, unknown>): Observable<TransportTrip> {
    return this.http.patch<TransportTrip>(this.url(`/transport/trips/${tripId}/status`), payload).pipe(tap(() => this.publish()));
  }

  updateLocation(tripId: string, payload: Record<string, unknown>): Observable<TransportTrip> {
    return this.http.post<TransportTrip>(this.url(`/transport/trips/${tripId}/location`), payload).pipe(tap(() => this.publish()));
  }

  listSchedules(): Observable<TransportSchedule[]> {
    return this.cache.get('transport:schedules', () => this.http.get<TransportSchedule[]>(this.url('/transport/schedules')));
  }

  createSchedule(payload: Partial<TransportSchedule> | Record<string, unknown>): Observable<TransportSchedule> {
    return this.http.post<TransportSchedule>(this.url('/transport/schedules'), payload).pipe(tap(() => this.publish()));
  }

  listMaintenance(): Observable<TransportMaintenance[]> {
    return this.cache.get('transport:maintenance', () => this.http.get<TransportMaintenance[]>(this.url('/transport/maintenance')));
  }

  createMaintenance(payload: Partial<TransportMaintenance> | Record<string, unknown>): Observable<TransportMaintenance> {
    return this.http.post<TransportMaintenance>(this.url('/transport/maintenance'), payload).pipe(tap(() => this.publish()));
  }

  listFuelLogs(): Observable<TransportFuelLog[]> {
    return this.cache.get('transport:fuel', () => this.http.get<TransportFuelLog[]>(this.url('/transport/fuel-logs')));
  }

  createFuelLog(payload: Partial<TransportFuelLog> | Record<string, unknown>): Observable<TransportFuelLog> {
    return this.http.post<TransportFuelLog>(this.url('/transport/fuel-logs'), payload).pipe(tap(() => this.publish()));
  }

  listSettings(): Observable<TransportSetting[]> {
    return this.cache.getPersistent('transport:settings', () => this.http.get<TransportSetting[]>(this.url('/transport/settings')));
  }

  upsertSetting(payload: Partial<TransportSetting> | Record<string, unknown>): Observable<TransportSetting> {
    return this.http.post<TransportSetting>(this.url('/transport/settings'), payload).pipe(tap(() => this.publish()));
  }

  report(params: Record<string, string | undefined>): Observable<TransportReport> {
    const query = this.query(params);
    return this.http.get<TransportReport>(this.url(`/transport/reports${query}`));
  }

  clearCache(): void {
    this.cache.clearPrefix('transport:');
  }

  private publish(): void {
    this.clearCache();
    this.dataSync.publish({
      name: 'data.updated',
      entityType: 'transport',
      modules: ['transport', 'er', 'opd', 'ipd', 'billing', 'inventory', 'hr', 'notifications', 'dashboard'],
      cachePrefixes: ['transport:', 'er:', 'opd:', 'ipd:', 'billing:', 'inventory:', 'hr:', 'notifications:', 'dashboard:'],
      message: 'Transport updates are available.',
    });
  }

  private query(params: Record<string, string | number | boolean | null | undefined>): string {
    const urlParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') {
        urlParams.set(key, String(value));
      }
    }
    const query = urlParams.toString();
    return query ? `?${query}` : '';
  }
}
