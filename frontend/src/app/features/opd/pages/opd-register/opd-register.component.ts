import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { OPDService } from '../../services/opd.service';

@Component({
  selector: 'app-opd-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './opd-register.component.html',
})
export class OPDRegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly opdService = inject(OPDService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  doctors: User[] = [];
  selectedPatient: Patient | null = null;

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    visit_date: [new Date().toISOString().slice(0, 10), Validators.required],
    department_name: ['General OPD', Validators.required],
    doctor_user_id: [''],
    consulting_doctor_name: ['', Validators.required],
    chief_complaint: [''],
    consultation_fee: [0, Validators.required],
    note: [''],
  });

  readonly patientLookupControl = this.fb.nonNullable.control('');

  constructor() {
    this.loadFormData();
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
  }

  loadFormData(): void {
    this.patientService.list().subscribe((patients) => {
      this.patients = patients;
      this.syncSelectedPatient();
    });
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
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

  onDoctorChanged(): void {
    const doctorId = this.form.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      return;
    }
    this.form.patchValue({ consulting_doctor_name: doctor.full_name });
  }

  onPatientChanged(): void {
    this.syncSelectedPatient();
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  backToQueue(): void {
    void this.router.navigate(['/opd']);
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    this.opdService.createVisit(this.form.getRawValue() as never).subscribe((visit) => {
      this.notificationService.success(`OPD visit ${visit.visit_number} created.`);
      this.form.reset({
        patient_id: '',
        visit_date: new Date().toISOString().slice(0, 10),
        department_name: 'General OPD',
        doctor_user_id: '',
        consulting_doctor_name: '',
        chief_complaint: '',
        consultation_fee: 0,
        note: '',
      });
      this.clearPatientSelection();
      void this.router.navigate(['/opd'], { queryParams: { openVisit: visit.id } });
    });
  }

  private syncSelectedPatient(): void {
    const patientId = this.form.getRawValue().patient_id;
    this.selectedPatient = this.patients.find((item) => item.id === patientId) ?? null;
  }
}
