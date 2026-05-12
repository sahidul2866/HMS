import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { ActionConfirmationService } from '../../../../core/services/action-confirmation.service';
import { PERMISSIONS } from '../../../../core/constants/permissions';
import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { IPDAdmission, IPDBed, IPDBedBoardRow, IPDDischargeReadiness, IPDHandoverBoard, IPDPatientWorkspace, IPDReportSummary, IPDSettings, IPDShiftCoverage, IPDStaffAvailability, IPDSummary } from '../../models/ipd.models';
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
  private readonly confirmationService = inject(ActionConfirmationService);
  readonly sessionService = inject(SessionService);
  readonly permissions = PERMISSIONS;
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  summary: IPDSummary | null = null;
  reportSummary: IPDReportSummary | null = null;
  admissions: IPDAdmission[] = [];
  beds: IPDBed[] = [];
  bedBoard: IPDBedBoardRow[] = [];
  doctors: User[] = [];
  selectedAdmission: IPDAdmission | null = null;
  workspace: IPDPatientWorkspace | null = null;
  dischargeReadiness: IPDDischargeReadiness | null = null;
  settings: IPDSettings | null = null;
  staffAvailability: IPDStaffAvailability[] = [];
  shiftCoverage: IPDShiftCoverage | null = null;
  handoverBoard: IPDHandoverBoard[] = [];
  activeWorkflow: 'notes' | 'orders' | 'meds' | 'handover' = 'notes';
  readonly transferForm = this.fb.group({
    bed_id: [''],
    ward_name: ['', Validators.required],
    bed_number: ['', Validators.required],
    transfer_reason: [''],
    transfer_time: [''],
    remarks: [''],
    note: [''],
  });

  readonly dischargeForm = this.fb.group({
    discharge_condition: ['Stable'],
    discharge_diagnosis: [''],
    discharge_summary: [''],
    discharge_note: [''],
    allow_override: [false],
    override_reason: [''],
  });

  readonly bedBoardFilters = this.fb.group({
    ward_name: [''],
    bed_type: [''],
    department_name: [''],
    status: [''],
  });

  readonly assignmentForm = this.fb.group({
    staff_user_id: ['', Validators.required],
    role_type: ['doctor', Validators.required],
    assignment_type: ['primary_consultant'],
    shift_name: ['morning'],
    reason: [''],
    allow_override: [false],
    override_reason: [''],
  });

  readonly clinicalNoteForm = this.fb.group({
    note_type: ['progress_note'],
    title: [''],
    note: ['', Validators.required],
    diagnosis: [''],
    treatment_plan: [''],
  });

  readonly nursingNoteForm = this.fb.group({
    note_type: ['nursing_note'],
    note: [''],
    temperature: [null as number | null],
    pulse: [null as number | null],
    respiratory_rate: [null as number | null],
    systolic_bp: [null as number | null],
    diastolic_bp: [null as number | null],
    spo2: [null as number | null],
    pain_score: [null as number | null],
    glucose: [null as number | null],
  });

  readonly orderForm = this.fb.group({
    order_type: ['medicine', Validators.required],
    service_area: ['pharmacy'],
    item_name: ['', Validators.required],
    instructions: [''],
    quantity: [1],
    priority: ['routine'],
    scheduled_at: [''],
    frequency: [''],
    duration: [''],
    dose: [''],
    route: [''],
  });

  readonly medicationForm = this.fb.group({
    order_id: [''],
    medicine_name: ['', Validators.required],
    dose: [''],
    route: ['oral'],
    frequency: [''],
    scheduled_at: [''],
    status: ['administered'],
    reason: [''],
    remarks: [''],
    allow_duplicate: [false],
  });

  readonly handoverForm = this.fb.group({
    handover_type: ['nursing'],
    shift_name: ['morning'],
    receiver_user_id: [''],
    summary: ['', Validators.required],
    pending_items: [''],
    precautions: [''],
    patient_condition: [''],
    active_diagnosis: [''],
    treatment_plan: [''],
    pending_orders: [''],
    medication_due: [''],
    abnormal_vitals: [''],
    critical_alerts: [''],
    discharge_tasks: [''],
    special_instructions: [''],
  });

  constructor() {
    this.loadAll();
    this.assignmentForm.get('role_type')?.valueChanges.subscribe((role) => {
      this.assignmentForm.patchValue({
        staff_user_id: '',
        assignment_type: role === 'nurse' ? 'primary_nurse' : 'primary_consultant',
      });
      this.loadStaffAvailability();
    });
    this.assignmentForm.get('shift_name')?.valueChanges.subscribe(() => {
      this.loadStaffAvailability();
      this.loadShiftCoverage();
    });
    this.route.queryParamMap.subscribe((params) => {
      const openAdmissionId = params.get('openAdmission');
      if (openAdmissionId) {
        this.ipdService.getAdmission(openAdmissionId).subscribe((admission) => this.selectAdmission(admission));
      }
    });
  }

  loadAll(): void {
    this.ipdService.getSummary().subscribe((summary) => (this.summary = summary));
    this.ipdService.reportSummary().subscribe((summary) => (this.reportSummary = summary));
    this.loadBedBoard();
    this.ipdService.listAdmissions().subscribe((admissions) => {
      this.admissions = admissions;
      if (this.selectedAdmission) {
        this.selectedAdmission = admissions.find((item) => item.id === this.selectedAdmission?.id) ?? null;
        if (this.selectedAdmission) {
          this.loadDischargeReadiness(this.selectedAdmission.id);
        }
      }
    });
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.ipdService.getSettings().subscribe((settings) => (this.settings = settings));
    this.loadHandoverBoard();
  }

  loadBedBoard(): void {
    this.ipdService.bedBoard(this.clean(this.bedBoardFilters.getRawValue())).subscribe((rows) => (this.bedBoard = rows));
  }

  resetBedBoardFilters(): void {
    this.bedBoardFilters.reset({ ward_name: '', bed_type: '', department_name: '', status: '' });
    this.loadBedBoard();
  }

  openBedBoardRow(row: IPDBedBoardRow): void {
    if (!row.admission_id) {
      return;
    }
    const admission = this.admissions.find((item) => item.id === row.admission_id);
    if (admission) {
      this.selectAdmission(admission);
      return;
    }
    this.ipdService.getAdmission(row.admission_id).subscribe((item) => this.selectAdmission(item));
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/ipd/admit' } });
  }

  navigateToAdmission(): void {
    void this.router.navigate(['/ipd/admit']);
  }

  navigateToAdmissionList(): void {
    void this.router.navigate(['/ipd/admissions']);
  }

  navigateToSettings(): void {
    void this.router.navigate(['/ipd/settings']);
  }

  discharge(admission: IPDAdmission): void {
    if (!this.confirmationService.confirmImportant(`Finalize discharge for ${admission.admission_number}?\n\nConfirm only after clinical and billing readiness has been reviewed.`)) {
      return;
    }
    this.ipdService.discharge(admission.id, this.dischargeForm.getRawValue() as never).subscribe((updated) => {
      this.selectedAdmission = updated;
      this.loadAll();
      this.notificationService.success(`Admission ${admission.admission_number} discharged. Final billing can now be reviewed.`);
    });
  }

  selectAdmission(admission: IPDAdmission): void {
    this.selectedAdmission = admission;
    this.loadWorkspace(admission.id);
    this.transferForm.patchValue({
      bed_id: '',
      ward_name: admission.ward_name,
      bed_number: admission.bed_number,
      transfer_reason: '',
      transfer_time: '',
      remarks: '',
      note: '',
    });
    this.dischargeForm.patchValue({
      discharge_condition: admission.discharge_condition || 'Stable',
      discharge_diagnosis: admission.discharge_diagnosis || admission.diagnosis || '',
      discharge_summary: admission.discharge_summary || '',
      discharge_note: admission.discharge_note || '',
      allow_override: false,
      override_reason: '',
    });
    this.loadDischargeReadiness(admission.id);
  }

  loadWorkspace(admissionId: string): void {
    this.ipdService.getWorkspace(admissionId).subscribe((workspace) => {
      this.workspace = workspace;
      this.selectedAdmission = workspace.admission;
      this.handoverForm.patchValue({
        patient_condition: workspace.admission.patient_condition || '',
        active_diagnosis: workspace.admission.diagnosis || '',
        pending_orders: this.pendingOrdersText,
        medication_due: this.dueMedicationText,
      });
      this.loadStaffAvailability();
      this.loadShiftCoverage();
      this.loadDischargeReadiness(admissionId);
    });
  }

  loadDischargeReadiness(admissionId: string): void {
    this.ipdService.dischargeReadiness(admissionId).subscribe((readiness) => (this.dischargeReadiness = readiness));
  }

  loadStaffAvailability(): void {
    if (!this.selectedAdmission) {
      return;
    }
    const value = this.assignmentForm.getRawValue();
    this.ipdService
      .listStaffAvailability({
        role_type: (value.role_type || 'doctor') as 'doctor' | 'nurse',
        ward_name: this.selectedAdmission.ward_name,
        department_name: this.selectedAdmission.department_name,
        shift_name: value.shift_name,
      })
      .subscribe((items) => (this.staffAvailability = items));
  }

  loadShiftCoverage(): void {
    if (!this.selectedAdmission) {
      return;
    }
    this.ipdService
      .getShiftCoverage({
        ward_name: this.selectedAdmission.ward_name,
        shift_name: this.assignmentForm.getRawValue().shift_name,
      })
      .subscribe((coverage) => (this.shiftCoverage = coverage));
  }

  loadHandoverBoard(): void {
    this.ipdService.listHandovers({ status: 'pending_ack' }).subscribe((items) => (this.handoverBoard = items));
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
        this.loadWorkspace(admission.id);
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

  get bedBoardStatuses(): string[] {
    return [...new Set(this.bedBoard.map((bed) => bed.board_status).filter(Boolean))].sort();
  }

  get bedBoardWards(): string[] {
    return [...new Set(this.bedBoard.map((bed) => bed.ward_name).filter(Boolean))].sort();
  }

  get bedBoardTypes(): string[] {
    return [...new Set(this.beds.map((bed) => bed.bed_type).filter(Boolean))].sort();
  }

  get activeDoctors() {
    return this.workspace?.admission.active_doctors || this.selectedAdmission?.active_doctors || [];
  }

  get activeNurses() {
    return this.workspace?.admission.active_nurses || this.selectedAdmission?.active_nurses || [];
  }

  get assignmentOptions(): Array<{ value: string; label: string }> {
    const values =
      this.assignmentForm.getRawValue().role_type === 'nurse'
        ? this.settings?.nurse_assignment_types || ['primary_nurse', 'duty_nurse']
        : this.settings?.doctor_assignment_types || ['admitting_doctor', 'primary_consultant', 'duty_doctor', 'specialist_consultant', 'on_call_doctor'];
    return values.map((value) => ({ value, label: value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) }));
  }

  get pendingOrdersText(): string {
    const pending = (this.workspace?.orders || []).filter((order) => !['completed', 'verified', 'cancelled'].includes(order.status));
    return pending.map((order) => `${order.item_name} (${order.status})`).join(', ');
  }

  get dueMedicationText(): string {
    const due = (this.workspace?.medications || []).filter((med) => med.status === 'due');
    return due.map((med) => `${med.medicine_name}${med.scheduled_at ? ' ' + new Date(med.scheduled_at).toLocaleTimeString() : ''}`).join(', ');
  }

  dischargeChecklist(admission: IPDAdmission): Array<{ label: string; done: boolean }> {
    if (this.dischargeReadiness?.admission_id === admission.id) {
      return this.dischargeReadiness.checks.map((item) => ({ label: item.label, done: item.done }));
    }
    return [
      { label: 'Doctor approval', done: !!this.dischargeForm.getRawValue().discharge_diagnosis || admission.status === 'discharged' },
      { label: 'Nursing clearance', done: (admission.pharmacy_clearance_status || '') === 'cleared' || admission.status === 'discharged' },
      { label: 'Billing review', done: (admission.billing_status || '') === 'cleared' || admission.status === 'discharged' },
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

  submitAssignment(): void {
    if (!this.selectedAdmission || this.assignmentForm.invalid) return;
    this.ipdService.assignStaff(this.selectedAdmission.id, this.clean(this.assignmentForm.getRawValue())).subscribe(() => {
      this.notificationService.success('Staff assignment saved.');
      this.loadWorkspace(this.selectedAdmission!.id);
      this.loadAll();
    });
  }

  submitClinicalNote(): void {
    if (!this.selectedAdmission || this.clinicalNoteForm.invalid) return;
    this.ipdService.createClinicalNote(this.selectedAdmission.id, this.clean(this.clinicalNoteForm.getRawValue())).subscribe(() => {
      this.notificationService.success('Clinical note saved.');
      this.clinicalNoteForm.patchValue({ title: '', note: '', diagnosis: '', treatment_plan: '' });
      this.loadWorkspace(this.selectedAdmission!.id);
    });
  }

  submitNursingNote(): void {
    if (!this.selectedAdmission) return;
    this.ipdService.createNursingNote(this.selectedAdmission.id, this.clean(this.nursingNoteForm.getRawValue())).subscribe(() => {
      this.notificationService.success('Nursing note saved.');
      this.nursingNoteForm.reset({ note_type: 'nursing_note' });
      this.loadWorkspace(this.selectedAdmission!.id);
    });
  }

  submitOrder(): void {
    if (!this.selectedAdmission || this.orderForm.invalid) return;
    this.ipdService.createOrder(this.selectedAdmission.id, this.clean(this.orderForm.getRawValue())).subscribe(() => {
      this.notificationService.success('IPD order created.');
      this.orderForm.patchValue({ item_name: '', instructions: '', quantity: 1, scheduled_at: '', frequency: '', duration: '', dose: '', route: '' });
      this.loadWorkspace(this.selectedAdmission!.id);
    });
  }

  submitMedication(): void {
    if (!this.selectedAdmission || this.medicationForm.invalid) return;
    this.ipdService.administerMedication(this.selectedAdmission.id, this.clean(this.medicationForm.getRawValue())).subscribe(() => {
      this.notificationService.success('Medication status recorded.');
      this.medicationForm.patchValue({ medicine_name: '', dose: '', frequency: '', reason: '', remarks: '', allow_duplicate: false });
      this.loadWorkspace(this.selectedAdmission!.id);
    });
  }

  recordScheduledMedication(medicineName: string, orderId?: string | null, scheduledAt?: string | null): void {
    if (!this.selectedAdmission) return;
    this.medicationForm.patchValue({ medicine_name: medicineName, order_id: orderId as never, scheduled_at: scheduledAt || '', status: 'administered' });
    this.activeWorkflow = 'meds';
  }

  completeTask(taskId: string): void {
    this.ipdService.updateNursingTask(taskId, { status: 'completed', completion_note: 'Completed from IPD workbench' }).subscribe(() => {
      this.notificationService.success('Nursing task completed.');
      if (this.selectedAdmission) this.loadWorkspace(this.selectedAdmission.id);
    });
  }

  discontinueOrder(orderId: string): void {
    if (!this.selectedAdmission) return;
    this.ipdService.updateOrderStatus(this.selectedAdmission.id, orderId, { status: 'discontinued', reason: 'Discontinued from IPD workbench' }).subscribe(() => {
      this.notificationService.success('Order discontinued.');
      this.loadWorkspace(this.selectedAdmission!.id);
    });
  }

  submitHandover(): void {
    if (!this.selectedAdmission || this.handoverForm.invalid) return;
    this.ipdService.createHandover(this.selectedAdmission.id, this.clean(this.handoverForm.getRawValue())).subscribe(() => {
      this.notificationService.success('Handover created.');
      this.handoverForm.patchValue({ summary: '', pending_items: '', precautions: '', critical_alerts: '', discharge_tasks: '', special_instructions: '' });
      this.loadWorkspace(this.selectedAdmission!.id);
      this.loadHandoverBoard();
    });
  }

  acknowledgeHandover(handoverId: string): void {
    this.ipdService.acknowledgeHandover(handoverId).subscribe(() => {
      this.notificationService.success('Handover acknowledged.');
      if (this.selectedAdmission) this.loadWorkspace(this.selectedAdmission.id);
      this.loadHandoverBoard();
    });
  }

  requestDischarge(): void {
    if (!this.selectedAdmission) return;
    this.ipdService.planDischarge(this.selectedAdmission.id).subscribe((admission) => {
      this.selectedAdmission = admission;
      this.loadAll();
      this.loadDischargeReadiness(admission.id);
      this.notificationService.success('Discharge requested.');
    });
  }

  private clean<T extends Record<string, unknown>>(value: T): T {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, item === '' ? null : item])) as T;
  }
}
