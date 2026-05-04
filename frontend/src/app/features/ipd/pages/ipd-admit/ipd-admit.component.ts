import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { FormValidationUi } from '../../../../shared/utils/form-validation';
import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { IPDBed } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-admit',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './ipd-admit.component.html',
  styleUrls: ['./ipd-admit.component.scss'],
})
export class IPDAdmitComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ipdService = inject(IPDService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly validation = FormValidationUi;

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  beds: IPDBed[] = [];
  doctors: User[] = [];
  selectedPatient: Patient | null = null;
  showPatientLookup = true;
  patientLookupModalOpen = false;
  submitted = false;
  saving = false;

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    department_name: ['General Medicine'],
    reference_name: [''],
    bed_id: [''],
    ward_filter: [''],
    admitted_at: [new Date().toISOString().slice(0, 16), Validators.required],
    booking_date: [new Date().toISOString().slice(0, 10)],
    booking_time: [new Date().toTimeString().slice(0, 5)],
    admission_type: ['General', Validators.required],
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    doctor_user_id: [''],
    attending_doctor_name: ['', Validators.required],
    diagnosis: [''],
    package_name: [''],
    intake_note: [''],
    emergency_contact_name: [''],
    emergency_contact_relation: [''],
    emergency_contact_phone: [''],
    daily_charge: [0, Validators.required],
    advance_amount: [0, Validators.required],
    expected_discharge_date: [''],
  });

  readonly patientLookupControl = this.fb.nonNullable.control('');

  constructor() {
    this.loadFormData();
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
    this.patientLookupControl.valueChanges.pipe(debounceTime(350), distinctUntilChanged()).subscribe((value) => {
      this.searchPatientsByTyping(value);
    });
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      if (patientId) {
        this.loadPatientContext(patientId);
      }
    });
  }

  loadFormData(): void {
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
    this.patientService.list().subscribe((patients) => {
      this.patients = patients;
      this.syncSelectedPatient();
    });
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
  }

  get availableBeds(): IPDBed[] {
    return this.beds.filter((bed) => bed.status === 'available');
  }

  get filteredBeds(): IPDBed[] {
    const wardFilter = this.form.getRawValue().ward_filter;
    if (!wardFilter) {
      return this.availableBeds;
    }
    return this.availableBeds.filter((bed) => bed.ward_name === wardFilter);
  }

  get bedMapItems(): IPDBed[] {
    const wardFilter = this.form.getRawValue().ward_filter;
    const beds = wardFilter ? this.beds.filter((bed) => bed.ward_name === wardFilter) : this.beds;
    return beds.slice(0, 18);
  }

  get wardOptions(): string[] {
    return [...new Set(this.beds.map((bed) => bed.ward_name).filter(Boolean))].sort((left, right) => left.localeCompare(right));
  }

  get admissionProgress(): number {
    const value = this.form.getRawValue();
    const checkpoints = [
      !!value.patient_id,
      !!value.doctor_user_id || !!value.attending_doctor_name,
      !!value.ward_name && !!value.bed_number,
      Number(value.advance_amount ?? 0) > 0,
      !!value.admitted_at,
    ];
    const completed = checkpoints.filter(Boolean).length;
    return Math.round((completed / checkpoints.length) * 100);
  }

  get admissionChecklist(): Array<{ label: string; done: boolean }> {
    const value = this.form.getRawValue();
    return [
      { label: 'Patient selected', done: !!value.patient_id },
      { label: 'Doctor assigned', done: !!value.doctor_user_id || !!value.attending_doctor_name },
      { label: 'Bed assigned', done: !!value.ward_name && !!value.bed_number },
      { label: 'Advance reviewed', done: Number(value.advance_amount || 0) > 0 },
      { label: 'Diagnosis noted', done: !!value.diagnosis },
    ];
  }

  get admissionTypeOptions(): string[] {
    return ['General', 'Emergency', 'Surgery', 'ICU', 'Maternity', 'Pediatric', 'Corporate', 'Insurance'];
  }

  get patientDisplayName(): string {
    if (!this.selectedPatient) {
      return 'No patient selected';
    }
    return `${this.selectedPatient.first_name} ${this.selectedPatient.last_name}`.trim();
  }

  get patientAgeLabel(): string {
    const dob = this.selectedPatient?.date_of_birth;
    if (!dob) {
      return 'Not recorded';
    }
    const birthDate = new Date(dob);
    if (Number.isNaN(birthDate.getTime())) {
      return 'Not recorded';
    }
    const now = new Date();
    let years = now.getFullYear() - birthDate.getFullYear();
    const monthDelta = now.getMonth() - birthDate.getMonth();
    if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birthDate.getDate())) {
      years -= 1;
    }
    return `${Math.max(years, 0)} yrs`;
  }

  get selectedBedSummary(): string {
    const selectedBed = this.beds.find((bed) => bed.id === this.form.getRawValue().bed_id);
    if (!selectedBed) {
      return `${this.form.getRawValue().ward_name || 'Ward'} / ${this.form.getRawValue().bed_number || 'Bed'}`;
    }
    return `${selectedBed.ward_name} / ${selectedBed.bed_number} / ${selectedBed.bed_type}`;
  }

  searchPatients(): void {
    const query = this.patientLookupControl.getRawValue().trim();
    if (query.length < 2) {
      this.patientSearchResults = [];
      return;
    }
    this.patientService.search(query).subscribe((results) => {
      this.patientSearchResults = results;
      this.patientLookupModalOpen = results.length > 0;
    });
  }

  private searchPatientsByTyping(raw: string): void {
    const query = raw.trim();
    if (query.length < 2) {
      this.patientSearchResults = [];
      this.patientLookupModalOpen = false;
      return;
    }
    this.patientService.search(query).subscribe((results) => {
      this.patientSearchResults = results.slice(0, 6);
      this.patientLookupModalOpen = false;
    });
  }

  applyPatient(result: PatientLookupResult): void {
    this.patchPatientContext({ ...result } as Patient, result.full_name);
    this.showPatientLookup = false;
    this.patientSearchResults = [];
    this.patientLookupModalOpen = false;
  }

  private loadPatientContext(patientId: string): void {
    this.patientService.get(patientId).subscribe((patient) => {
      this.patchPatientContext(patient);
      this.showPatientLookup = false;
    });
  }

  private patchPatientContext(patient: Patient, fullName = `${patient.first_name} ${patient.last_name}`.trim()): void {
    this.form.patchValue({ patient_id: patient.id });
    this.selectedPatient = patient;
    this.patientLookupControl.setValue(`${patient.patient_number} - ${fullName}`);
    this.form.patchValue({
      emergency_contact_name: patient.emergency_contact_name || '',
      emergency_contact_phone: patient.emergency_contact_phone || '',
    });
  }

  clearPatientSelection(): void {
    this.form.patchValue({
      patient_id: '',
      emergency_contact_name: '',
      emergency_contact_phone: '',
    });
    this.selectedPatient = null;
    this.showPatientLookup = true;
    this.patientLookupControl.setValue('');
    this.patientSearchResults = [];
    this.patientLookupModalOpen = false;
  }

  openPatientLookupModal(): void {
    if (!this.patientSearchResults.length) {
      return;
    }
    this.patientLookupModalOpen = true;
  }

  closePatientLookupModal(): void {
    this.patientLookupModalOpen = false;
  }

  onBedChanged(): void {
    const bedId = this.form.getRawValue().bed_id;
    const selectedBed = this.beds.find((bed) => bed.id === bedId);
    if (!selectedBed) {
      return;
    }
    this.form.patchValue({
      ward_filter: selectedBed.ward_name,
      ward_name: selectedBed.ward_name,
      bed_number: selectedBed.bed_number,
      daily_charge: selectedBed.daily_rate,
    });
  }

  selectBed(bed: IPDBed): void {
    if (String(bed.status).toLowerCase() !== 'available') {
      this.notificationService.warning(`${bed.ward_name} / ${bed.bed_number} is ${bed.status}. Choose an available bed.`);
      return;
    }
    this.form.patchValue({
      bed_id: bed.id,
      ward_filter: bed.ward_name,
      ward_name: bed.ward_name,
      bed_number: bed.bed_number,
      daily_charge: bed.daily_rate,
    });
  }

  bedStatusClass(bed: IPDBed): string {
    return `bed-tile bed-tile--${String(bed.status).toLowerCase()} ${this.form.getRawValue().bed_id === bed.id ? 'bed-tile--selected' : ''}`;
  }

  onWardFilterChanged(): void {
    const wardFilter = this.form.getRawValue().ward_filter;
    const currentBedId = this.form.getRawValue().bed_id;
    if (!wardFilter) {
      return;
    }
    const currentBed = this.availableBeds.find((bed) => bed.id === currentBedId);
    if (currentBed && currentBed.ward_name === wardFilter) {
      return;
    }
    this.form.patchValue({ bed_id: '' });
  }

  onDoctorChanged(): void {
    const doctorId = this.form.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      return;
    }
    this.form.patchValue({ attending_doctor_name: doctor.full_name });
  }

  onPatientChanged(): void {
    this.syncSelectedPatient();
    if (this.selectedPatient) {
      this.showPatientLookup = false;
    }
  }

  enablePatientLookup(): void {
    this.showPatientLookup = true;
    this.patientLookupControl.setValue('');
    this.patientSearchResults = [];
    this.patientLookupModalOpen = false;
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/ipd/admit' } });
  }

  backToOverview(): void {
    void this.router.navigate(['/ipd']);
  }

  submit(): void {
    this.submitted = true;
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    const value = this.form.getRawValue();
    this.ipdService.createAdmission({ ...value, expected_discharge_date: value.expected_discharge_date || null } as never).subscribe((admission) => {
      this.saving = false;
      this.submitted = false;
      this.notificationService.success(`Admission ${admission.admission_number} created.`);
      this.form.reset({
        patient_id: '',
        bed_id: '',
        admitted_at: new Date().toISOString().slice(0, 16),
        admission_type: 'General',
        ward_name: 'Ward A',
        bed_number: '',
        doctor_user_id: '',
        attending_doctor_name: '',
        diagnosis: '',
        daily_charge: 0,
        advance_amount: 0,
        expected_discharge_date: '',
      });
      this.clearPatientSelection();
      void this.router.navigate(['/ipd'], { queryParams: { openAdmission: admission.id } });
    }, () => {
      this.saving = false;
    });
  }

  private syncSelectedPatient(): void {
    const patientId = this.form.getRawValue().patient_id;
    this.selectedPatient = this.patients.find((item) => item.id === patientId) ?? null;
    if (this.selectedPatient) {
      this.form.patchValue({
        emergency_contact_name: this.selectedPatient.emergency_contact_name || this.form.getRawValue().emergency_contact_name,
        emergency_contact_phone: this.selectedPatient.emergency_contact_phone || this.form.getRawValue().emergency_contact_phone,
      });
    }
  }

  get selectedDoctorName(): string {
    const doctorId = this.form.getRawValue().doctor_user_id;
    return this.doctors.find((item) => item.id === doctorId)?.full_name || this.form.getRawValue().attending_doctor_name || 'Pending';
  }
}
