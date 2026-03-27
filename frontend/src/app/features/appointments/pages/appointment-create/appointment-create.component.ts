import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { AppointmentsService } from '../../services/appointments.service';

@Component({
  selector: 'app-appointment-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './appointment-create.component.html',
  styleUrls: ['./appointment-create.component.scss'],
})
export class AppointmentCreateComponent {
  private readonly fb = inject(FormBuilder);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  doctors: User[] = [];
  selectedPatient: Patient | null = null;
  saving = false;

  readonly patientLookupControl = this.fb.nonNullable.control('');

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    doctor_user_id: ['', Validators.required],
    appointment_at: ['', Validators.required],
    reason: [''],
    note: [''],
  });

  constructor() {
    this.loadPatients();
    this.loadDoctors();
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      if (patientId) {
        this.form.patchValue({ patient_id: patientId });
        this.syncSelectedPatient();
      }
    });
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
  }

  loadPatients(): void {
    this.patientService.list().subscribe((patients) => {
      this.patients = patients;
      this.syncSelectedPatient();
    });
  }

  loadDoctors(): void {
    this.doctorDirectoryService.listDoctors(true).subscribe((doctors) => (this.doctors = doctors));
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

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/appointments/create' } });
  }

  openAppointmentDesk(): void {
    void this.router.navigate(['/appointments']);
  }

  submit(): void {
    if (this.form.invalid || this.saving) {
      return;
    }

    const raw = this.form.getRawValue();
    this.saving = true;
    this.appointmentsService
      .create({
        patient_id: raw.patient_id || '',
        doctor_user_id: raw.doctor_user_id || '',
        appointment_at: raw.appointment_at || '',
        reason: raw.reason?.trim() || null,
        note: raw.note?.trim() || null,
      })
      .subscribe({
        next: (appointment) => {
          this.saving = false;
          this.notificationService.success(`Appointment ${appointment.appointment_number} created successfully.`);
          void this.router.navigate(['/appointments']);
        },
        error: () => {
          this.saving = false;
        },
      });
  }

  formatPatient(patient: Patient): string {
    return `${patient.patient_number} - ${patient.first_name} ${patient.last_name}`;
  }

  private syncSelectedPatient(): void {
    const patientId = this.form.getRawValue().patient_id;
    this.selectedPatient = this.patients.find((item) => item.id === patientId) ?? null;
  }
}
