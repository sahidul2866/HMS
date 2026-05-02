import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { IPDAdmission, IPDBed, IPDSummary } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './ipd-overview.component.html',
  styleUrls: ['./ipd-overview.component.scss'],
})
export class IPDOverviewComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ipdService = inject(IPDService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  readonly sessionService = inject(SessionService);
  readonly permissions = PERMISSIONS;
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  summary: IPDSummary | null = null;
  admissions: IPDAdmission[] = [];
  beds: IPDBed[] = [];
  doctors: User[] = [];
  selectedAdmission: IPDAdmission | null = null;

  readonly bedForm = this.fb.group({
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    bed_type: ['General', Validators.required],
    daily_rate: [0, Validators.required],
    note: [''],
  });

  readonly transferForm = this.fb.group({
    bed_id: [''],
    ward_name: ['', Validators.required],
    bed_number: ['', Validators.required],
    note: [''],
  });

  readonly dischargeForm = this.fb.group({
    discharge_condition: ['Stable'],
    discharge_diagnosis: [''],
    discharge_summary: [''],
    discharge_note: [''],
  });

  constructor() {
    this.loadAll();
    this.route.queryParamMap.subscribe((params) => {
      const openAdmissionId = params.get('openAdmission');
      if (openAdmissionId) {
        this.ipdService.getAdmission(openAdmissionId).subscribe((admission) => this.selectAdmission(admission));
      }
    });
  }

  loadAll(): void {
    this.ipdService.getSummary().subscribe((summary) => (this.summary = summary));
    this.ipdService.listAdmissions().subscribe((admissions) => {
      this.admissions = admissions;
      if (this.selectedAdmission) {
        this.selectedAdmission = admissions.find((item) => item.id === this.selectedAdmission?.id) ?? null;
      }
    });
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/ipd/admit' } });
  }

  navigateToAdmission(): void {
    void this.router.navigate(['/ipd/admit']);
  }

  submitBed(): void {
    if (this.bedForm.invalid) {
      return;
    }
    this.ipdService.createBed(this.bedForm.getRawValue() as never).subscribe((bed) => {
      this.bedForm.reset({
        ward_name: 'Ward A',
        bed_number: '',
        bed_type: 'General',
        daily_rate: 0,
        note: '',
      });
      this.loadAll();
      this.notificationService.success(`Bed ${bed.ward_name} / ${bed.bed_number} created.`);
    });
  }

  discharge(admission: IPDAdmission): void {
    this.ipdService.discharge(admission.id, this.dischargeForm.getRawValue() as never).subscribe((updated) => {
      this.selectedAdmission = updated;
      this.loadAll();
      this.notificationService.success(`Admission ${admission.admission_number} discharged.`);
    });
  }

  selectAdmission(admission: IPDAdmission): void {
    this.selectedAdmission = admission;
    this.transferForm.patchValue({
      bed_id: '',
      ward_name: admission.ward_name,
      bed_number: admission.bed_number,
      note: '',
    });
    this.dischargeForm.patchValue({
      discharge_condition: admission.discharge_condition || 'Stable',
      discharge_diagnosis: admission.discharge_diagnosis || admission.diagnosis || '',
      discharge_summary: admission.discharge_summary || '',
      discharge_note: admission.discharge_note || '',
    });
  }

  openBillingForAdmission(admission: IPDAdmission, stage: 'interim' | 'final' = 'interim'): void {
    void this.router.navigate(['/billing/create'], {
      queryParams: {
        patientId: admission.patient.id,
        ipdAdmissionId: admission.id,
        billingStage: stage,
      },
    });
  }

  transferAdmission(): void {
    if (!this.selectedAdmission || this.transferForm.invalid) {
      return;
    }
    const value = this.transferForm.getRawValue();
    this.ipdService
      .transfer(this.selectedAdmission.id, {
        ...value,
        bed_id: value.bed_id || null,
      } as never)
      .subscribe((admission) => {
        this.selectedAdmission = admission;
        this.loadAll();
        this.notificationService.success(`Admission ${admission.admission_number} transferred.`);
      });
  }

  get availableBeds(): IPDBed[] {
    return this.beds.filter((bed) => bed.status === 'available');
  }

  get occupiedBeds(): IPDBed[] {
    return this.beds.filter((bed) => bed.status === 'occupied');
  }

  get activeAdmissions(): IPDAdmission[] {
    return this.admissions.filter((admission) => admission.status !== 'discharged');
  }

  get dischargedAdmissions(): IPDAdmission[] {
    return this.admissions.filter((admission) => admission.status === 'discharged');
  }

  get admissionsByWard(): Array<{ ward: string; count: number; width: string }> {
    const counts = new Map<string, number>();
    for (const admission of this.activeAdmissions) {
      counts.set(admission.ward_name, (counts.get(admission.ward_name) ?? 0) + 1);
    }
    const rows = [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
    const max = Math.max(...rows.map(([, count]) => count), 1);
    return rows.map(([ward, count]) => ({
      ward,
      count,
      width: `${Math.max((count / max) * 100, count > 0 ? 16 : 0)}%`,
    }));
  }

  get bedOccupancyPercent(): number {
    if (!this.beds.length) {
      return 0;
    }
    return Math.round((this.occupiedBeds.length / this.beds.length) * 100);
  }

  get longStayAdmissions(): IPDAdmission[] {
    const now = Date.now();
    return this.activeAdmissions.filter((admission) => {
      const admitted = new Date(admission.admitted_at).getTime();
      return Number.isFinite(admitted) && now - admitted > 5 * 24 * 60 * 60 * 1000;
    });
  }

  get ipdQuickStats(): Array<{ label: string; value: string | number; tone: string }> {
    return [
      { label: 'Available Beds', value: this.availableBeds.length, tone: 'good' },
      { label: 'Occupied Beds', value: this.occupiedBeds.length, tone: 'warn' },
      { label: 'Long Stay', value: this.longStayAdmissions.length, tone: this.longStayAdmissions.length ? 'danger' : 'good' },
      { label: 'Pending Bills', value: this.activeAdmissions.length, tone: 'info' },
      { label: 'Today Discharge', value: this.dischargedAdmissions.filter((item) => (item.discharged_at || '').slice(0, 10) === new Date().toISOString().slice(0, 10)).length, tone: 'good' },
    ];
  }

  dischargeChecklist(admission: IPDAdmission): Array<{ label: string; done: boolean }> {
    return [
      { label: 'Doctor approval', done: !!this.dischargeForm.getRawValue().discharge_diagnosis || admission.status === 'discharged' },
      { label: 'Nursing clearance', done: admission.movements.length > 0 || admission.status === 'discharged' },
      { label: 'Billing review', done: Number(admission.advance_amount || 0) > 0 || admission.status === 'discharged' },
      { label: 'Summary ready', done: !!this.dischargeForm.getRawValue().discharge_summary || admission.status === 'discharged' },
    ];
  }

  onTransferBedChanged(): void {
    const bedId = this.transferForm.getRawValue().bed_id;
    const selectedBed = this.beds.find((bed) => bed.id === bedId);
    if (!selectedBed) {
      return;
    }
    this.transferForm.patchValue({
      ward_name: selectedBed.ward_name,
      bed_number: selectedBed.bed_number,
    });
  }
}
