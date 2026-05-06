import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged, finalize } from 'rxjs';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { FormValidationUi } from '../../../../shared/utils/form-validation';
import { CreatePatientPayload, Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { AppointmentsService } from '../../services/appointments.service';
import { DoctorSlotAvailability } from '../../models/appointment.models';

@Component({
  selector: 'app-appointment-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, PatientContextPanelComponent],
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
  readonly validation = FormValidationUi;

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  doctors: User[] = [];
  selectedPatient: Patient | null = null;
  patientLookupModalOpen = false;
  loadingSlots = false;
  slots: DoctorSlotAvailability[] = [];
  selectedSlot: DoctorSlotAvailability | null = null;
  saving = false;
  submitted = false;
  private completed = false;

  readonly patientLookupControl = this.fb.nonNullable.control('');

  readonly form = this.fb.group({
    patient_id: [''],
    first_name: [''],
    last_name: [''],
    phone: [''],
    email: ['', Validators.email],
    gender: [''],
    date_of_birth: [''],
    address: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
    doctor_user_id: ['', Validators.required],
    slot_date: [new Date().toISOString().slice(0, 10), Validators.required],
    reason: [''],
    note: [''],
  });

  constructor() {
    this.loadPatients();
    this.loadDoctors();
    this.patientLookupControl.valueChanges.pipe(debounceTime(350), distinctUntilChanged()).subscribe((value) => {
      this.searchPatients(value);
    });
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      if (patientId) {
        this.form.patchValue({ patient_id: patientId });
        this.syncSelectedPatient();
      }
    });
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
    this.form.controls.doctor_user_id.valueChanges.subscribe(() => this.loadSlots());
    this.form.controls.slot_date.valueChanges.subscribe(() => this.loadSlots());
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

  loadSlots(): void {
    const doctorId = this.form.controls.doctor_user_id.getRawValue();
    const slotDate = this.form.controls.slot_date.getRawValue();
    this.selectedSlot = null;
    this.slots = [];
    if (!doctorId || !slotDate) {
      return;
    }
    this.loadingSlots = true;
    this.appointmentsService
      .getDoctorSlots(doctorId, slotDate)
      .pipe(finalize(() => (this.loadingSlots = false)))
      .subscribe((response) => {
        this.slots = response.slots;
      });
  }

  selectSlot(slot: DoctorSlotAvailability): void {
    if (slot.status !== 'available') {
      return;
    }
    this.selectedSlot = slot;
  }

  searchPatients(value?: string): void {
    const query = (value ?? this.patientLookupControl.getRawValue()).trim();
    if (query.length < 2) {
      this.patientSearchResults = [];
      this.patientLookupModalOpen = false;
      return;
    }
    this.patientService.search(query).subscribe((results) => {
      this.patientSearchResults = results;
      this.patientLookupModalOpen = false;
    });
  }

  applyPatient(result: PatientLookupResult): void {
    this.form.patchValue({ patient_id: result.id });
    this.selectedPatient =
      this.patients.find((item) => item.id === result.id) ??
      ({
        ...result,
      } as Patient);
    this.form.patchValue({
      first_name: this.selectedPatient.first_name || '',
      last_name: this.selectedPatient.last_name || '',
      phone: this.selectedPatient.phone || '',
      email: this.selectedPatient.email || '',
      gender: this.selectedPatient.gender || '',
      date_of_birth: this.selectedPatient.date_of_birth || '',
      address: this.selectedPatient.address || '',
      emergency_contact_name: this.selectedPatient.emergency_contact_name || '',
      emergency_contact_phone: this.selectedPatient.emergency_contact_phone || '',
    });
    this.patientLookupControl.setValue(`${result.patient_number} - ${result.full_name}`);
    this.patientSearchResults = [];
    this.patientLookupModalOpen = false;
  }

  clearPatientSelection(): void {
    this.form.patchValue({
      patient_id: '',
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      gender: '',
      date_of_birth: '',
      address: '',
      emergency_contact_name: '',
      emergency_contact_phone: '',
    });
    this.selectedPatient = null;
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

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/appointments/create' } });
  }

  openAppointmentDesk(): void {
    void this.router.navigate(['/appointments']);
  }

  hasUnsavedChanges(): boolean {
    return !this.completed && !this.saving && (this.form.dirty || this.patientLookupControl.dirty || !!this.selectedSlot);
  }

  submit(): void {
    this.submitted = true;
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    if (!this.selectedSlot) {
      this.notificationService.warning('Please select an available slot.');
      return;
    }

    const raw = this.form.getRawValue();
    this.saving = true;

    const createAppointment = (patientId: string) => {
      this.appointmentsService
        .create({
          patient_id: patientId,
          doctor_user_id: raw.doctor_user_id || '',
          slot_start_at: this.selectedSlot?.slot_start_at || null,
          reason: raw.reason?.trim() || null,
          note: raw.note?.trim() || null,
        })
        .subscribe({
          next: (appointment) => {
            this.saving = false;
            this.submitted = false;
            this.completed = true;
            this.form.markAsPristine();
            this.patientLookupControl.markAsPristine();
            this.notificationService.success(`Appointment ${appointment.appointment_number} created successfully.`);
            void this.router.navigate(['/appointments']);
          },
          error: () => {
            this.saving = false;
          },
        });
    };

    if (raw.patient_id) {
      createAppointment(raw.patient_id);
      return;
    }

    if (!raw.first_name?.trim() || !raw.last_name?.trim()) {
      this.saving = false;
      this.notificationService.warning('First name and last name are required for new patient appointment.');
      return;
    }

    const payload: CreatePatientPayload = {
      first_name: raw.first_name.trim(),
      last_name: raw.last_name.trim(),
      phone: raw.phone?.trim() || null,
      email: raw.email?.trim() || null,
      gender: raw.gender?.trim() || null,
      date_of_birth: raw.date_of_birth || null,
      address: raw.address?.trim() || null,
      emergency_contact_name: raw.emergency_contact_name?.trim() || null,
      emergency_contact_phone: raw.emergency_contact_phone?.trim() || null,
    };
    this.patientService.create(payload).subscribe({
      next: (patient) => createAppointment(patient.id),
      error: () => {
        this.saving = false;
      },
    });
  }

  formatPatient(patient: Patient): string {
    return `${patient.patient_number} - ${patient.first_name} ${patient.last_name}`;
  }

  get selectedDoctorName(): string {
    const doctorId = this.form.getRawValue().doctor_user_id;
    return this.doctors.find((item) => item.id === doctorId)?.full_name || 'Pending';
  }

  get selectedScheduleLabel(): string {
    if (!this.selectedSlot) {
      return 'Pending';
    }
    return `${this.formatTime(this.selectedSlot.slot_start_at)} - ${this.formatTime(this.selectedSlot.slot_end_at)}`;
  }

  formatTime(value: string): string {
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  private syncSelectedPatient(): void {
    const patientId = this.form.getRawValue().patient_id;
    this.selectedPatient = this.patients.find((item) => item.id === patientId) ?? null;
    if (this.selectedPatient) {
      this.form.patchValue({
        first_name: this.selectedPatient.first_name || '',
        last_name: this.selectedPatient.last_name || '',
        phone: this.selectedPatient.phone || '',
        email: this.selectedPatient.email || '',
        gender: this.selectedPatient.gender || '',
        date_of_birth: this.selectedPatient.date_of_birth || '',
        address: this.selectedPatient.address || '',
        emergency_contact_name: this.selectedPatient.emergency_contact_name || '',
        emergency_contact_phone: this.selectedPatient.emergency_contact_phone || '',
      });
    }
  }
}
