import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import {
  CreateIPDAdmissionPayload,
  CreateIPDBedPayload,
  DischargeIPDAdmissionPayload,
  IPDAdmission,
  IPDBedBoardRow,
  IPDBed,
  IPDBillingSummary,
  IPDDischargeReadiness,
  IPDHandoverBoard,
  IPDMedicationAdministration,
  IPDNursingTask,
  IPDPatientWorkspace,
  IPDReportSummary,
  IPDShiftCoverage,
  IPDStaffAvailability,
  IPDSettings,
  IPDSummary,
  IPDVitalsTrend,
  TransferIPDAdmissionPayload,
} from '../models/ipd.models';

@Injectable({ providedIn: 'root' })
export class IPDService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  listAdmissions(): Observable<IPDAdmission[]> {
    return this.cache.get('ipd:admissions', () => this.http.get<IPDAdmission[]>(this.url('/ipd/admissions')));
  }

  getAdmission(admissionId: string): Observable<IPDAdmission> {
    return this.cache.get(`ipd:admission:${admissionId}`, () => this.http.get<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}`)));
  }

  getWorkspace(admissionId: string): Observable<IPDPatientWorkspace> {
    return this.cache.get(`ipd:workspace:${admissionId}`, () => this.http.get<IPDPatientWorkspace>(this.url(`/ipd/admissions/${admissionId}/workspace`)));
  }

  getSummary(): Observable<IPDSummary> {
    return this.cache.get('ipd:summary', () => this.http.get<IPDSummary>(this.url('/ipd/summary')));
  }

  bedBoard(params: { ward_name?: string | null; room_type?: string | null; bed_type?: string | null; department_name?: string | null; status?: string | null } = {}): Observable<IPDBedBoardRow[]> {
    return this.http.get<IPDBedBoardRow[]>(this.url('/ipd/bed-board'), { params: this.cleanParams(params) });
  }

  reportSummary(): Observable<IPDReportSummary> {
    return this.cache.get('ipd:reports:summary', () => this.http.get<IPDReportSummary>(this.url('/ipd/reports/summary')));
  }

  getSettings(): Observable<IPDSettings> {
    return this.cache.getPersistent('ipd:settings', () => this.http.get<IPDSettings>(this.url('/ipd/settings')));
  }

  updateSettings(payload: IPDSettings): Observable<IPDSettings> {
    return this.http.put<IPDSettings>(this.url('/ipd/settings'), payload).pipe(tap(() => this.clearCache()));
  }

  listStaffAvailability(params: {
    role_type: 'doctor' | 'nurse';
    ward_name?: string | null;
    department_name?: string | null;
    shift_name?: string | null;
    q?: string | null;
  }): Observable<IPDStaffAvailability[]> {
    return this.http.get<IPDStaffAvailability[]>(this.url('/ipd/staff-availability'), { params: this.cleanParams(params) });
  }

  getShiftCoverage(params: { ward_name?: string | null; shift_name?: string | null }): Observable<IPDShiftCoverage> {
    return this.http.get<IPDShiftCoverage>(this.url('/ipd/shift-coverage'), { params: this.cleanParams(params) });
  }

  listHandovers(params: { status?: string | null; ward_name?: string | null; q?: string | null } = {}): Observable<IPDHandoverBoard[]> {
    return this.http.get<IPDHandoverBoard[]>(this.url('/ipd/handovers'), { params: this.cleanParams(params) });
  }

  createAdmission(payload: CreateIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url('/ipd/admissions'), payload).pipe(
      tap((admission) => {
        this.clearCache();
        this.publishAdmissionEvent('ipd.bed.assigned', admission, 'IPD admission updated.');
      })
    );
  }

  listBeds(): Observable<IPDBed[]> {
    return this.cache.get('ipd:beds', () => this.http.get<IPDBed[]>(this.url('/ipd/beds')));
  }

  createBed(payload: CreateIPDBedPayload): Observable<IPDBed> {
    return this.http.post<IPDBed>(this.url('/ipd/beds'), payload).pipe(
      tap((bed) => {
        this.clearCache();
        this.dataSync.publish({
          name: 'ipd.bed.assigned',
          entityType: 'ipd_bed',
          entityId: bed.id,
          modules: ['ipd', 'er', 'dashboard'],
          cachePrefixes: ['ipd:', 'er:', 'dashboard:'],
          message: 'Bed board updated.',
        });
      })
    );
  }

  discharge(admissionId: string, payload: DischargeIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.put<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}/discharge`), payload).pipe(
      tap((admission) => {
        this.clearCache();
        this.publishAdmissionEvent('data.updated', admission, 'IPD admission status updated.');
      })
    );
  }

  dischargeReadiness(admissionId: string): Observable<IPDDischargeReadiness> {
    return this.http.get<IPDDischargeReadiness>(this.url(`/ipd/admissions/${admissionId}/discharge-readiness`));
  }

  billingSummary(admissionId: string): Observable<IPDBillingSummary> {
    return this.http.get<IPDBillingSummary>(this.url(`/ipd/admissions/${admissionId}/billing-summary`));
  }

  transfer(admissionId: string, payload: TransferIPDAdmissionPayload): Observable<IPDAdmission> {
    return this.http.put<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}/transfer`), payload).pipe(
      tap((admission) => {
        this.clearCache();
        this.publishAdmissionEvent('ipd.bed.assigned', admission, 'Bed assignment updated.');
      })
    );
  }

  assignStaff(admissionId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/ipd/admissions/${admissionId}/assignments`), payload).pipe(tap(() => this.clearCache()));
  }

  createClinicalNote(admissionId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/ipd/admissions/${admissionId}/clinical-notes`), payload).pipe(tap(() => this.clearCache()));
  }

  createNursingNote(admissionId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/ipd/admissions/${admissionId}/nursing-notes`), payload).pipe(tap(() => this.clearCache()));
  }

  createOrder(admissionId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/ipd/admissions/${admissionId}/orders`), payload).pipe(tap(() => this.clearCache()));
  }

  updateOrderStatus(admissionId: string, orderId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.patch(this.url(`/ipd/admissions/${admissionId}/orders/${orderId}`), payload).pipe(tap(() => this.clearCache()));
  }

  administerMedication(admissionId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/ipd/admissions/${admissionId}/medications`), payload).pipe(tap(() => this.clearCache()));
  }

  medicationSchedule(params: { ward_name?: string | null; nurse_user_id?: string | null; shift_name?: string | null; status?: string | null } = {}): Observable<IPDMedicationAdministration[]> {
    return this.http.get<IPDMedicationAdministration[]>(this.url('/ipd/medications/schedule'), { params: this.cleanParams(params) });
  }

  nursingTasks(params: { ward_name?: string | null; nurse_user_id?: string | null; shift_name?: string | null; status?: string | null } = {}): Observable<IPDNursingTask[]> {
    return this.http.get<IPDNursingTask[]>(this.url('/ipd/nursing-tasks'), { params: this.cleanParams(params) });
  }

  updateNursingTask(taskId: string, payload: Record<string, unknown>): Observable<IPDNursingTask> {
    return this.http.patch<IPDNursingTask>(this.url(`/ipd/nursing-tasks/${taskId}`), payload).pipe(tap(() => this.clearCache()));
  }

  vitalsTrends(admissionId: string): Observable<IPDVitalsTrend[]> {
    return this.http.get<IPDVitalsTrend[]>(this.url(`/ipd/admissions/${admissionId}/vitals-trends`));
  }

  createHandover(admissionId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(this.url(`/ipd/admissions/${admissionId}/handovers`), payload).pipe(tap(() => this.clearCache()));
  }

  acknowledgeHandover(handoverId: string): Observable<unknown> {
    return this.http.post(this.url(`/ipd/handovers/${handoverId}/acknowledge`), {}).pipe(tap(() => this.clearCache()));
  }

  planDischarge(admissionId: string, status = 'requested'): Observable<IPDAdmission> {
    return this.http.post<IPDAdmission>(this.url(`/ipd/admissions/${admissionId}/discharge-plan?status=${encodeURIComponent(status)}`), {}).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('ipd:');
  }

  private publishAdmissionEvent(name: 'ipd.bed.assigned' | 'data.updated', admission: IPDAdmission, message: string): void {
    this.dataSync.publish({
      name,
      entityType: 'ipd_admission',
      entityId: admission.id,
      patientId: admission.patient?.id,
      modules: ['ipd', 'patients', 'billing', 'er', 'dashboard'],
      cachePrefixes: ['ipd:', 'patients:', 'billing:', 'er:', 'dashboard:'],
      message,
    });
  }

  private cleanParams(params: Record<string, string | null | undefined>): Record<string, string> {
    return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== null && value !== undefined && value !== '').map(([key, value]) => [key, String(value)]));
  }
}
