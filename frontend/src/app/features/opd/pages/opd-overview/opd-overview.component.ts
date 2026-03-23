import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { IPDBed } from '../../../ipd/models/ipd.models';
import { IPDService } from '../../../ipd/services/ipd.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { OPDSummary, OPDVisit } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

@Component({
  selector: 'app-opd-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './opd-overview.component.html',
})
export class OPDOverviewComponent {
  private readonly fb = inject(FormBuilder);
  private readonly opdService = inject(OPDService);
  private readonly ipdService = inject(IPDService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  summary: OPDSummary | null = null;
  visits: OPDVisit[] = [];
  patients: Patient[] = [];
  doctors: User[] = [];
  beds: IPDBed[] = [];
  selectedVisit: OPDVisit | null = null;

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

  readonly orderForm = this.fb.group({
    order_type: ['prescription', Validators.required],
    service_area: [''],
    item_name: ['', Validators.required],
    instructions: [''],
    quantity: [1, Validators.required],
  });

  readonly convertForm = this.fb.group({
    admitted_at: [new Date().toISOString().slice(0, 16), Validators.required],
    admission_type: ['General', Validators.required],
    bed_id: [''],
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    doctor_user_id: [''],
    attending_doctor_name: ['', Validators.required],
    diagnosis: [''],
    daily_charge: [0, Validators.required],
    advance_amount: [0, Validators.required],
    expected_discharge_date: [''],
  });

  constructor() {
    this.loadAll();
  }

  loadAll(): void {
    this.opdService.getSummary().subscribe((summary) => (this.summary = summary));
    this.opdService.listVisits().subscribe((visits) => {
      this.visits = visits;
      if (this.selectedVisit) {
        this.selectedVisit = visits.find((item) => item.id === this.selectedVisit?.id) ?? null;
      }
    });
    this.patientService.list().subscribe((patients) => (this.patients = patients));
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd' } });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    this.opdService.createVisit(this.form.getRawValue() as never).subscribe((visit) => {
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
      this.loadAll();
      this.notificationService.success(`OPD visit ${visit.visit_number} created.`);
    });
  }

  setStatus(visit: OPDVisit, status: string): void {
    this.opdService.updateStatus(visit.id, status).subscribe(() => {
      this.loadAll();
      this.notificationService.success(`Visit ${visit.visit_number} moved to ${status.replace('_', ' ')}.`);
    });
  }

  selectVisit(visit: OPDVisit): void {
    this.selectedVisit = visit;
    this.convertForm.patchValue({
      admitted_at: new Date().toISOString().slice(0, 16),
      admission_type: 'General',
      bed_id: '',
      ward_name: 'Ward A',
      bed_number: '',
      doctor_user_id: visit.consulting_doctor_user_id || visit.doctor_user_id || '',
      attending_doctor_name: visit.consulting_doctor_name,
      diagnosis: visit.chief_complaint || '',
      daily_charge: 0,
      advance_amount: 0,
      expected_discharge_date: '',
    });
  }

  submitOrder(): void {
    if (!this.selectedVisit || this.orderForm.invalid) {
      return;
    }
    const payload = this.orderForm.getRawValue();
    this.opdService.createOrder(this.selectedVisit.id, payload as never).subscribe((visit) => {
      this.selectedVisit = visit;
      this.loadAll();
      this.orderForm.reset({ order_type: 'prescription', service_area: '', item_name: '', instructions: '', quantity: 1 });
      this.notificationService.success(`${visit.visit_number} updated with ${payload.order_type || 'order'}.`);
    });
  }

  onDoctorChanged(): void {
    const doctorId = this.form.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      return;
    }
    this.form.patchValue({ consulting_doctor_name: doctor.full_name });
  }

  onOrderTypeChanged(): void {
    if (this.orderForm.getRawValue().order_type !== 'investigation') {
      this.orderForm.patchValue({ service_area: '' });
    }
  }

  get availableBeds(): IPDBed[] {
    return this.beds.filter((bed) => bed.status === 'available');
  }

  onConvertBedChanged(): void {
    const bedId = this.convertForm.getRawValue().bed_id;
    const bed = this.beds.find((item) => item.id === bedId);
    if (!bed) {
      return;
    }
    this.convertForm.patchValue({
      ward_name: bed.ward_name,
      bed_number: bed.bed_number,
      daily_charge: Number(bed.daily_rate),
    });
  }

  onConvertDoctorChanged(): void {
    const doctorId = this.convertForm.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      return;
    }
    this.convertForm.patchValue({ attending_doctor_name: doctor.full_name });
  }

  convertToIPD(): void {
    if (!this.selectedVisit || this.selectedVisit.converted_ipd_admission_id || this.convertForm.invalid) {
      return;
    }

    const value = this.convertForm.getRawValue();
    this.opdService
      .convertToIPD(this.selectedVisit.id, {
        ...value,
        expected_discharge_date: value.expected_discharge_date || null,
      } as never)
      .subscribe((admission) => {
        this.loadAll();
        this.notificationService.success(`Visit ${this.selectedVisit?.visit_number} converted to ${admission.admission_number}.`);
      });
  }
}
