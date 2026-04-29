import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';
import {
  HRAttendance,
  HRDashboardSummary,
  HRDesignation,
  HREmployee,
  HRLeaveRequest,
  HRLeaveType,
  HRPayrollRun,
  HRRoster,
  HRSetting,
  HRShift,
  PaginatedResponse,
} from '../models/hr.models';

@Injectable({ providedIn: 'root' })
export class HRService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  dashboard(): Observable<HRDashboardSummary> {
    return this.cache.get('hr:dashboard', () => this.http.get<HRDashboardSummary>(this.url('/hr/dashboard')));
  }

  listEmployees(params: { q?: string; status?: string; page?: number; page_size?: number } = {}): Observable<PaginatedResponse<HREmployee>> {
    const query = this.query(params);
    return this.cache.getPersistent(`hr:employees:${query}`, () => this.http.get<PaginatedResponse<HREmployee>>(this.url(`/hr/employees${query}`)));
  }

  createEmployee(payload: Partial<HREmployee>): Observable<HREmployee> {
    return this.http.post<HREmployee>(this.url('/hr/employees'), payload).pipe(tap(() => this.clearHRCache()));
  }

  updateEmployee(id: string, payload: Partial<HREmployee>): Observable<HREmployee> {
    return this.http.put<HREmployee>(this.url(`/hr/employees/${id}`), payload).pipe(tap(() => this.clearHRCache()));
  }

  listDesignations(): Observable<HRDesignation[]> {
    return this.cache.getPersistent('hr:designations', () => this.http.get<HRDesignation[]>(this.url('/hr/designations')));
  }

  createDesignation(payload: Partial<HRDesignation>): Observable<HRDesignation> {
    return this.http.post<HRDesignation>(this.url('/hr/designations'), payload).pipe(tap(() => this.clearHRCache()));
  }

  listAttendance(attendanceDate?: string): Observable<HRAttendance[]> {
    const query = attendanceDate ? `?attendance_date=${attendanceDate}` : '';
    return this.cache.get(`hr:attendance:${query}`, () => this.http.get<HRAttendance[]>(this.url(`/hr/attendance${query}`)));
  }

  markAttendance(payload: Partial<HRAttendance>): Observable<HRAttendance> {
    return this.http.post<HRAttendance>(this.url('/hr/attendance'), payload).pipe(tap(() => this.clearHRCache()));
  }

  listShifts(): Observable<HRShift[]> {
    return this.cache.getPersistent('hr:shifts', () => this.http.get<HRShift[]>(this.url('/hr/shifts')));
  }

  createShift(payload: Partial<HRShift>): Observable<HRShift> {
    return this.http.post<HRShift>(this.url('/hr/shifts'), payload).pipe(tap(() => this.clearHRCache()));
  }

  listRoster(): Observable<HRRoster[]> {
    return this.cache.get('hr:roster', () => this.http.get<HRRoster[]>(this.url('/hr/roster')));
  }

  createRoster(payload: Partial<HRRoster>): Observable<HRRoster> {
    return this.http.post<HRRoster>(this.url('/hr/roster'), payload).pipe(tap(() => this.clearHRCache()));
  }

  listLeaveTypes(): Observable<HRLeaveType[]> {
    return this.cache.getPersistent('hr:leave-types', () => this.http.get<HRLeaveType[]>(this.url('/hr/leave-types')));
  }

  listLeaveRequests(): Observable<HRLeaveRequest[]> {
    return this.cache.get('hr:leave-requests', () => this.http.get<HRLeaveRequest[]>(this.url('/hr/leave-requests')));
  }

  requestLeave(payload: Partial<HRLeaveRequest>): Observable<HRLeaveRequest> {
    return this.http.post<HRLeaveRequest>(this.url('/hr/leave-requests'), payload).pipe(tap(() => this.clearHRCache()));
  }

  decideLeave(id: string, action: 'approve' | 'reject'): Observable<HRLeaveRequest> {
    return this.http.post<HRLeaveRequest>(this.url(`/hr/leave-requests/${id}/${action}`), {}).pipe(tap(() => this.clearHRCache()));
  }

  upsertSalary(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/salary-structures'), payload).pipe(tap(() => this.clearHRCache()));
  }

  createOvertime(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/overtime'), payload).pipe(tap(() => this.clearHRCache()));
  }

  createLoan(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/loans'), payload).pipe(tap(() => this.clearHRCache()));
  }

  listPayrollRuns(): Observable<HRPayrollRun[]> {
    return this.cache.get('hr:payroll-runs', () => this.http.get<HRPayrollRun[]>(this.url('/hr/payroll/runs')));
  }

  processPayroll(payload: { payroll_month: string; department_id?: string | null; note?: string | null }): Observable<HRPayrollRun> {
    return this.http.post<HRPayrollRun>(this.url('/hr/payroll/process'), payload).pipe(tap(() => this.clearHRCache()));
  }

  decidePayroll(id: string, status: string): Observable<HRPayrollRun> {
    return this.http.post<HRPayrollRun>(this.url(`/hr/payroll/runs/${id}/${status}`), {}).pipe(tap(() => this.clearHRCache()));
  }

  createRecruitmentJob(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/recruitment/jobs'), payload).pipe(tap(() => this.clearHRCache()));
  }

  createCandidate(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/recruitment/candidates'), payload).pipe(tap(() => this.clearHRCache()));
  }

  createPerformance(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/performance'), payload).pipe(tap(() => this.clearHRCache()));
  }

  createResignation(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.url('/hr/resignations'), payload).pipe(tap(() => this.clearHRCache()));
  }

  listSettings(): Observable<HRSetting[]> {
    return this.cache.getPersistent('hr:settings', () => this.http.get<HRSetting[]>(this.url('/hr/settings')));
  }

  updateSetting(key: string, payload: Partial<HRSetting>): Observable<HRSetting> {
    return this.http.put<HRSetting>(this.url(`/hr/settings/${key}`), payload).pipe(tap(() => this.clearHRCache()));
  }

  clearHRCache(): void {
    this.cache.clearPrefix('hr:');
  }

  private query(params: Record<string, string | number | null | undefined>): string {
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
