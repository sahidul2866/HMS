import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { FormValidationUi } from '../../../../shared/utils/form-validation';
import { CreatePatientPayload, Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { CreateOPDVisitPayload } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

type PatientSearchContext = 'lookup' | 'phone' | 'email' | null;

@Component({
  selector: 'app-opd-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './opd-register.component.html',
  styleUrls: ['./opd-register.component.scss'],
})
export class OPDRegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly opdService = inject(OPDService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly validation = FormValidationUi;

  patientSearchResults: PatientLookupResult[] = [];
  doctors: User[] = [];
  selectedPatient: Patient | null = null;
  activePatientSearchContext: PatientSearchContext = null;
  submitted = false;
  saving = false;
  isFollowUpAllowed = false;

  readonly form = this.fb.group({
    patient_id: [''],
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    phone: [''],
    email: ['', Validators.email],
    gender: [''],
    date_of_birth: [''],
    address: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
    visit_date: [new Date().toISOString().slice(0, 10), Validators.required],
    department_name: ['General OPD', Validators.required],
    doctor_user_id: [''],
    consulting_doctor_name: ['', Validators.required],
    consultation_fee: [0, Validators.required],
    visit_type: ['new', Validators.required],
    chief_complaint: [''],
    note: [''],
  });

  readonly patientLookupControl = this.fb.nonNullable.control('');

  constructor() {
    this.loadFormData();
    this.patientLookupControl.valueChanges.pipe(debounceTime(500), distinctUntilChanged()).subscribe((value) => {
      this.searchPatients(value, 'lookup');
    });
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      if (patientId) {
        this.loadPatientContext(patientId);
      }
    });
  }

  loadFormData(): void {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
  }

  searchPatients(query: string, context: PatientSearchContext): void {
    const normalized = query.trim();
    if (normalized.length < 3) {
      if (this.activePatientSearchContext === context) {
        this.closePatientSearch();
      }
      return;
    }

    this.patientService.searchByAnyField(normalized, 5).subscribe((results) => {
      this.patientSearchResults = results;
      this.activePatientSearchContext = results.length ? context : null;
    });
  }

  applyPatient(result: PatientLookupResult): void {
    this.patchPatientContext({ ...result } as Patient, result.full_name);
    this.closePatientSearch();
    // Check follow-up eligibility if doctor is selected
    const doctorId = this.form.getRawValue().doctor_user_id;
    if (doctorId) {
      const doctor = this.doctors.find(d => d.id === doctorId);
      if (doctor) {
        this.checkFollowUpEligibility(doctor);
      }
    }
  }

  private loadPatientContext(patientId: string): void {
    this.patientService.get(patientId).subscribe((patient) => {
      this.patchPatientContext(patient);
      const doctorId = this.form.getRawValue().doctor_user_id;
      const doctor = doctorId ? this.doctors.find((item) => item.id === doctorId) : null;
      if (doctor) {
        this.checkFollowUpEligibility(doctor);
      }
    });
  }

  private patchPatientContext(patient: Patient, fullName = `${patient.first_name} ${patient.last_name}`.trim()): void {
    this.selectedPatient = patient;
    this.form.patchValue(
      {
        patient_id: patient.id,
        first_name: patient.first_name,
        last_name: patient.last_name,
        phone: patient.phone || '',
        email: patient.email || '',
        gender: patient.gender || '',
        date_of_birth: patient.date_of_birth || '',
        address: patient.address || '',
        emergency_contact_name: patient.emergency_contact_name || '',
        emergency_contact_phone: patient.emergency_contact_phone || '',
      },
      { emitEvent: false }
    );
    this.patientLookupControl.setValue(`${patient.patient_number} - ${fullName}`, { emitEvent: false });
  }

  clearPatientSelection(): void {
    this.selectedPatient = null;
    this.patientLookupControl.setValue('', { emitEvent: false });
    this.form.patchValue(
      {
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
      },
      { emitEvent: false }
    );
    this.closePatientSearch();
  }

  closePatientSearch(): void {
    this.patientSearchResults = [];
    this.activePatientSearchContext = null;
  }

  showSearchContext(context: PatientSearchContext): boolean {
    return this.activePatientSearchContext === context && this.patientSearchResults.length > 0;
  }

  onDoctorChanged(): void {
    const doctorId = this.form.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      this.isFollowUpAllowed = false;
      return;
    }
    this.form.patchValue({
      consulting_doctor_name: doctor.full_name,
      consultation_fee: Number(doctor.opd_consultation_fee ?? 0),
    });
    this.checkFollowUpEligibility(doctor);
  }

  onVisitTypeChanged(): void {
    const value = this.form.getRawValue();
    if (value.visit_type === 'follow_up' && !this.isFollowUpAllowed) {
      this.form.patchValue({ visit_type: 'new' });
      this.notificationService.warning('Follow-up visit is not available. Please select "New Visit" instead.');
    }
  }

  private checkFollowUpEligibility(doctor: User): void {
    const patientId = this.form.getRawValue().patient_id;
    if (!patientId || !doctor.id) {
      this.isFollowUpAllowed = false;
      return;
    }

    // Check if there's a previous visit to this doctor within the follow-up period
    this.opdService.getPatientVisits(patientId).subscribe((visits) => {
      const doctorVisits = visits.filter(v => v.consulting_doctor_user_id === doctor.id && 
                                               ['completed', 'waiting', 'in_consultation', 'billed', 'prescribed'].includes(v.status));
      if (doctorVisits.length === 0) {
        this.isFollowUpAllowed = false;
        return;
      }

      const lastVisit = doctorVisits.sort((a, b) => new Date(b.visit_date || '').getTime() - new Date(a.visit_date || '').getTime())[0];
      const currentVisitDate = this.form.getRawValue().visit_date;
      if (!lastVisit.visit_date || !currentVisitDate) {
        this.isFollowUpAllowed = false;
        return;
      }
      const daysSinceLastVisit = Math.floor((new Date(currentVisitDate).getTime() - new Date(lastVisit.visit_date).getTime()) / (1000 * 60 * 60 * 24));
      this.isFollowUpAllowed = daysSinceLastVisit <= (doctor.opd_follow_up_days ?? 30);
    });
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  backToQueue(): void {
    void this.router.navigate(['/opd']);
  }

  submit(): void {
    this.submitted = true;
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    // Additional validation for follow-up visits
    if (value.visit_type === 'follow_up' && !this.isFollowUpAllowed) {
      this.notificationService.error('Follow-up visit is not allowed for this patient and doctor combination.');
      return;
    }

    this.saving = true;
    const createVisit = (patientId: string) => {
      const payload: CreateOPDVisitPayload = {
        patient_id: patientId,
        visit_date: value.visit_date ?? new Date().toISOString().slice(0, 10),
        department_name: value.department_name ?? 'General OPD',
        doctor_user_id: value.doctor_user_id || null,
        consulting_doctor_name: value.consulting_doctor_name ?? '',
        consultation_fee: Number(value.consultation_fee ?? 0),
        visit_type: value.visit_type ?? 'new',
        chief_complaint: value.chief_complaint || null,
        note: value.note || null,
      };

      this.opdService.createVisit(payload).subscribe({
        next: (visit) => {
          this.saving = false;
          this.submitted = false;
          this.notificationService.success(`OPD visit ${visit.visit_number} created.`);
          void this.router.navigate(['/opd'], { queryParams: { openVisit: visit.id } });
          this.resetForm();
        },
        error: () => {
          this.saving = false;
        },
      });
    };

    if (value.patient_id) {
      createVisit(value.patient_id);
      return;
    }

    const patientPayload: CreatePatientPayload = {
      first_name: value.first_name ?? '',
      last_name: value.last_name ?? '',
      phone: value.phone || null,
      email: value.email || null,
      gender: value.gender || null,
      date_of_birth: value.date_of_birth || null,
      address: value.address || null,
      emergency_contact_name: value.emergency_contact_name || null,
      emergency_contact_phone: value.emergency_contact_phone || null,
    };

    this.patientService.create(patientPayload).subscribe({
      next: (patient) => createVisit(patient.id),
      error: () => {
        this.saving = false;
      },
    });
  }

  get hasExistingPatientSelection(): boolean {
    return !!this.form.getRawValue().patient_id;
  }

  get selectedDoctorName(): string {
    const doctorId = this.form.getRawValue().doctor_user_id;
    return this.doctors.find((item) => item.id === doctorId)?.full_name || this.form.getRawValue().consulting_doctor_name || 'Pending';
  }

  private resetForm(): void {
    this.form.reset({
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
      visit_date: new Date().toISOString().slice(0, 10),
      department_name: 'General OPD',
      doctor_user_id: '',
      consulting_doctor_name: '',
      consultation_fee: 0,
      visit_type: 'new',
      chief_complaint: '',
      note: '',
    });
    this.selectedPatient = null;
    this.patientLookupControl.setValue('', { emitEvent: false });
    this.closePatientSearch();
    this.isFollowUpAllowed = false;
  }
}
