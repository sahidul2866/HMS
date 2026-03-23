import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { IPDAdmission, IPDBed, IPDSummary } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './ipd-overview.component.html',
})
export class IPDOverviewComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ipdService = inject(IPDService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  summary: IPDSummary | null = null;
  admissions: IPDAdmission[] = [];
  patients: Patient[] = [];
  beds: IPDBed[] = [];
  doctors: User[] = [];

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

  readonly bedForm = this.fb.group({
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    bed_type: ['General', Validators.required],
    daily_rate: [0, Validators.required],
    note: [''],
  });

  constructor() {
    this.loadAll();
  }

  loadAll(): void {
    this.ipdService.getSummary().subscribe((summary) => (this.summary = summary));
    this.ipdService.listAdmissions().subscribe((admissions) => (this.admissions = admissions));
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
    this.patientService.list().subscribe((patients) => (this.patients = patients));
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/ipd' } });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const value = this.form.getRawValue();
    this.ipdService.createAdmission({ ...value, expected_discharge_date: value.expected_discharge_date || null } as never).subscribe((admission) => {
      this.loadAll();
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
      this.notificationService.success(`Admission ${admission.admission_number} created.`);
    });
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
    this.ipdService.discharge(admission.id, 'Discharged from IPD workflow').subscribe(() => {
      this.loadAll();
      this.notificationService.success(`Admission ${admission.admission_number} discharged.`);
    });
  }

  get availableBeds(): IPDBed[] {
    return this.beds.filter((bed) => bed.status === 'available');
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
}
