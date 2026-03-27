import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { IPDBed } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-admit',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './ipd-admit.component.html',
})
export class IPDAdmitComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ipdService = inject(IPDService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  beds: IPDBed[] = [];
  doctors: User[] = [];
  selectedPatient: Patient | null = null;

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    bed_id: [''],
    admitted_at: [new Date().toISOString().slice(0, 16), Validators.required],
    admission_type: ['General', Validators.required],
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    doctor_user_id: [''],
    attending_doctor_name: ['', Validators.required],
    diagnosis: [''],
    daily_charge: [0, Validators.required],
    advance_amount: [0, Validators.required],
    expected_discharge_date: [''],
  });

  readonly patientLookupControl = this.fb.nonNullable.control('');

  constructor() {
    this.loadFormData();
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
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

  searchPatients(): void {
    const query = this.patientLookupControl.getRawValue().trim();
    if (query.length < 2) {
      this.patientSearchResults = [];
      return;
    }
    this.patientService.search(query).subscribe((results) => (this.patientSearchResults = results));
  }

  applyPatient(result: PatientLookupResult): void {
    this.form.patchValue({ patient_id: result.id });
    this.selectedPatient =
      this.patients.find((item) => item.id === result.id) ??
      ({
        ...result,
      } as Patient);
    this.patientLookupControl.setValue(`${result.patient_number} - ${result.full_name}`);
    this.patientSearchResults = [];
  }

  clearPatientSelection(): void {
    this.form.patchValue({ patient_id: '' });
    this.selectedPatient = null;
    this.patientLookupControl.setValue('');
    this.patientSearchResults = [];
  }

  onBedChanged(): void {
    const bedId = this.form.getRawValue().bed_id;
    const selectedBed = this.beds.find((bed) => bed.id === bedId);
    if (!selectedBed) {
      return;
    }
    this.form.patchValue({
      ward_name: selectedBed.ward_name,
      bed_number: selectedBed.bed_number,
      daily_charge: selectedBed.daily_rate,
    });
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
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/ipd/admit' } });
  }

  backToOverview(): void {
    void this.router.navigate(['/ipd']);
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const value = this.form.getRawValue();
    this.ipdService.createAdmission({ ...value, expected_discharge_date: value.expected_discharge_date || null } as never).subscribe((admission) => {
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
    });
  }

  private syncSelectedPatient(): void {
    const patientId = this.form.getRawValue().patient_id;
    this.selectedPatient = this.patients.find((item) => item.id === patientId) ?? null;
  }
}
