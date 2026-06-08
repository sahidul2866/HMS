import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import { AppDataEventName, DataSyncService } from '../../../core/services/data-sync.service';
import {
  CateringDashboard,
  CateringDietOrder,
  CateringDietType,
  CateringMealPlan,
  CateringMealSchedule,
  CateringMealTask,
  CateringReport,
  CateringSetting,
  CateringStaffMeal,
} from '../models/catering.models';

@Injectable({ providedIn: 'root' })
export class CateringService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  dashboard(params: Record<string, string | number | null | undefined> = {}): Observable<CateringDashboard> {
    const query = this.query(params);
    return this.cache.get(`catering:dashboard:${query}`, () => this.http.get<CateringDashboard>(this.url(`/catering/dashboard${query}`)));
  }

  listDietTypes(): Observable<CateringDietType[]> {
    return this.cache.getPersistent('catering:diet-types', () => this.http.get<CateringDietType[]>(this.url('/catering/diet-types')));
  }

  createDietType(payload: Partial<CateringDietType> | Record<string, unknown>): Observable<CateringDietType> {
    return this.http.post<CateringDietType>(this.url('/catering/diet-types'), payload).pipe(tap(() => this.clearCache()));
  }

  listMealPlans(): Observable<CateringMealPlan[]> {
    return this.cache.getPersistent('catering:meal-plans', () => this.http.get<CateringMealPlan[]>(this.url('/catering/meal-plans')));
  }

  createMealPlan(payload: Partial<CateringMealPlan> | Record<string, unknown>): Observable<CateringMealPlan> {
    return this.http.post<CateringMealPlan>(this.url('/catering/meal-plans'), payload).pipe(tap(() => this.clearCache()));
  }

  listSchedules(): Observable<CateringMealSchedule[]> {
    return this.cache.getPersistent('catering:schedules', () => this.http.get<CateringMealSchedule[]>(this.url('/catering/schedules')));
  }

  upsertSchedule(payload: Partial<CateringMealSchedule> | Record<string, unknown>): Observable<CateringMealSchedule> {
    return this.http.post<CateringMealSchedule>(this.url('/catering/schedules'), payload).pipe(tap(() => this.clearCache()));
  }

  listDietOrders(params: Record<string, string | boolean | undefined> = {}): Observable<CateringDietOrder[]> {
    const query = this.query(params);
    return this.cache.get(`catering:diet-orders:${query}`, () => this.http.get<CateringDietOrder[]>(this.url(`/catering/diet-orders${query}`)));
  }

  createDietOrder(payload: Partial<CateringDietOrder> | Record<string, unknown>): Observable<CateringDietOrder> {
    return this.http.post<CateringDietOrder>(this.url('/catering/diet-orders'), payload).pipe(tap((order) => this.publish('catering.diet_order.created', order.patient_id)));
  }

  approveDietOrder(id: string): Observable<CateringDietOrder> {
    return this.http.post<CateringDietOrder>(this.url(`/catering/diet-orders/${id}/approve`), {}).pipe(tap((order) => this.publish('catering.diet_order.approved', order.patient_id)));
  }

  generateMeals(mealDate: string): Observable<CateringMealTask[]> {
    return this.http.post<CateringMealTask[]>(this.url('/catering/meals/generate'), { meal_date: mealDate }).pipe(tap(() => this.clearCache()));
  }

  listMeals(params: Record<string, string | undefined> = {}): Observable<CateringMealTask[]> {
    const query = this.query(params);
    return this.cache.get(`catering:meals:${query}`, () => this.http.get<CateringMealTask[]>(this.url(`/catering/meals${query}`)));
  }

  updateMealStatus(id: string, payload: Record<string, unknown>): Observable<CateringMealTask> {
    return this.http.patch<CateringMealTask>(this.url(`/catering/meals/${id}/status`), payload).pipe(tap((task) => this.publish('catering.meal.updated', task.patient_id)));
  }

  listStaffMeals(mealDate?: string): Observable<CateringStaffMeal[]> {
    const query = this.query({ meal_date: mealDate });
    return this.cache.get(`catering:staff-meals:${query}`, () => this.http.get<CateringStaffMeal[]>(this.url(`/catering/staff-meals${query}`)));
  }

  createStaffMeal(payload: Partial<CateringStaffMeal> | Record<string, unknown>): Observable<CateringStaffMeal> {
    return this.http.post<CateringStaffMeal>(this.url('/catering/staff-meals'), payload).pipe(tap(() => this.clearCache()));
  }

  updateStaffMealStatus(id: string, status: string): Observable<CateringStaffMeal> {
    return this.http.patch<CateringStaffMeal>(this.url(`/catering/staff-meals/${id}/${status}`), {}).pipe(tap(() => this.clearCache()));
  }

  listSettings(): Observable<CateringSetting[]> {
    return this.cache.getPersistent('catering:settings', () => this.http.get<CateringSetting[]>(this.url('/catering/settings')));
  }

  upsertSetting(payload: Partial<CateringSetting> | Record<string, unknown>): Observable<CateringSetting> {
    return this.http.post<CateringSetting>(this.url('/catering/settings'), payload).pipe(tap(() => this.clearCache()));
  }

  report(params: Record<string, string | undefined>): Observable<CateringReport> {
    const query = this.query(params);
    return this.http.get<CateringReport>(this.url(`/catering/reports${query}`));
  }

  clearCache(): void {
    this.cache.clearPrefix('catering:');
  }

  private publish(name: AppDataEventName, patientId?: string | null): void {
    this.clearCache();
    this.dataSync.publish({
      name,
      entityType: 'catering',
      patientId,
      modules: ['catering', 'ipd', 'er', 'billing', 'inventory', 'dashboard', 'notifications'],
      cachePrefixes: ['catering:', 'ipd:', 'er:', 'billing:', 'inventory:', 'dashboard:', 'notifications:'],
      message: 'Catering updates are available.',
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
