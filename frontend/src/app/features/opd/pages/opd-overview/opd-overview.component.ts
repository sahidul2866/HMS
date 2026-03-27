import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AppointmentsService } from '../../../appointments/services/appointments.service';
import { IPDBed } from '../../../ipd/models/ipd.models';
import { IPDService } from '../../../ipd/services/ipd.service';
import { OPDSummary, OPDVisit, OPDVisitOrder, UpdateOPDConsultationPayload } from '../../models/opd.models';
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
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  summary: OPDSummary | null = null;
  visits: OPDVisit[] = [];
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

  readonly consultationForm = this.fb.group({
    chief_complaint: [''],
    history_of_present_illness: [''],
    past_history: [''],
    vital_signs: [''],
    examination_note: [''],
    provisional_diagnosis: [''],
    final_diagnosis: [''],
    follow_up_date: [''],
    follow_up_note: [''],
    note: [''],
  });

  readonly followUpForm = this.fb.group({
    doctor_user_id: [''],
    appointment_at: [''],
    reason: [''],
    note: [''],
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
    this.route.queryParamMap.subscribe((params) => {
      const openVisitId = params.get('openVisit');
      if (openVisitId) {
        this.opdService.getVisit(openVisitId).subscribe((visit) => (this.selectedVisit = visit));
      }
    });
  }

  loadAll(): void {
    this.opdService.getSummary().subscribe((summary) => (this.summary = summary));
    this.opdService.listVisits().subscribe((visits) => {
      this.visits = visits;
      if (this.selectedVisit) {
        this.selectedVisit = visits.find((item) => item.id === this.selectedVisit?.id) ?? null;
      }
    });
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  setStatus(visit: OPDVisit, status: string): void {
    this.opdService.updateStatus(visit.id, status).subscribe(() => {
      this.loadAll();
      this.notificationService.success(`Visit ${visit.visit_number} moved to ${status.replace('_', ' ')}.`);
    });
  }

  selectVisit(visit: OPDVisit): void {
    this.selectedVisit = visit;
    this.consultationForm.patchValue({
      chief_complaint: visit.chief_complaint || '',
      history_of_present_illness: visit.history_of_present_illness || '',
      past_history: visit.past_history || '',
      vital_signs: visit.vital_signs || '',
      examination_note: visit.examination_note || '',
      provisional_diagnosis: visit.provisional_diagnosis || '',
      final_diagnosis: visit.final_diagnosis || '',
      follow_up_date: visit.follow_up_date || '',
      follow_up_note: visit.follow_up_note || '',
      note: visit.note || '',
    });
    this.followUpForm.patchValue({
      doctor_user_id: visit.consulting_doctor_user_id || '',
      appointment_at: this.buildDefaultFollowUpDateTime(visit.follow_up_date || ''),
      reason: visit.follow_up_note || visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
      note: visit.note || '',
    });
    this.convertForm.patchValue({
      admitted_at: new Date().toISOString().slice(0, 16),
      admission_type: 'General',
      bed_id: '',
      ward_name: 'Ward A',
      bed_number: '',
      doctor_user_id: visit.consulting_doctor_user_id || visit.doctor_user_id || '',
      attending_doctor_name: visit.consulting_doctor_name,
      diagnosis: visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
      daily_charge: 0,
      advance_amount: 0,
      expected_discharge_date: '',
    });
  }

  saveConsultation(): void {
    if (!this.selectedVisit) {
      return;
    }
    const payload = this.consultationForm.getRawValue() as UpdateOPDConsultationPayload;
    this.opdService
      .updateConsultation(this.selectedVisit.id, {
        ...payload,
        follow_up_date: payload.follow_up_date || null,
      })
      .subscribe((visit) => {
        this.selectedVisit = visit;
        this.followUpForm.patchValue({
          appointment_at: this.buildDefaultFollowUpDateTime(visit.follow_up_date || ''),
          reason: visit.follow_up_note || visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
          note: visit.note || '',
        });
        this.loadAll();
        this.notificationService.success(`Consultation notes saved for ${visit.visit_number}.`);
      });
  }

  createFollowUpAppointment(): void {
    if (!this.selectedVisit || this.followUpForm.invalid) {
      return;
    }

    const value = this.followUpForm.getRawValue();
    if (!value.doctor_user_id || !value.appointment_at) {
      return;
    }

    this.appointmentsService
      .create({
        patient_id: this.selectedVisit.patient.id,
        doctor_user_id: value.doctor_user_id,
        appointment_at: value.appointment_at,
        reason: value.reason || this.selectedVisit.follow_up_note || this.selectedVisit.final_diagnosis || null,
        note: value.note || `Follow-up from ${this.selectedVisit.visit_number}`,
      })
      .subscribe((appointment) => {
        this.notificationService.success(`Follow-up appointment ${appointment.appointment_number} created.`);
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

  updateProcedureOrder(order: OPDVisitOrder, status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled'): void {
    if (!this.selectedVisit) {
      return;
    }

    const resultText =
      status === 'completed'
        ? window.prompt('Enter procedure outcome or note', order.result_text || order.instructions || '')
        : order.result_text || null;
    if (status === 'completed' && resultText === null) {
      return;
    }

    this.opdService
      .updateOrder(this.selectedVisit.id, order.id, {
        status,
        result_text: resultText || null,
      })
      .subscribe((visit) => {
        this.selectedVisit = visit;
        this.loadAll();
        this.notificationService.success(`Procedure ${order.item_name} moved to ${status.replace('_', ' ')}.`);
      });
  }

  getOrderTypeCount(type: string): number {
    return this.selectedVisit?.orders.filter((order) => order.order_type === type).length ?? 0;
  }

  openBilling(visit: OPDVisit): void {
    void this.router.navigate(['/billing/create'], {
      queryParams: {
        patientId: visit.patient.id,
        opdVisitId: visit.id,
      },
    });
  }

  printPrescription(visit: OPDVisit): void {
    const prescriptionOrders = visit.orders.filter((order) => order.order_type === 'prescription');
    if (!prescriptionOrders.length) {
      this.notificationService.info(`No prescription orders available for ${visit.visit_number}.`);
      return;
    }

    const popup = window.open('', '_blank', 'width=960,height=720');
    if (!popup) {
      return;
    }

    popup.document.write(`
      <html>
        <head>
          <title>${visit.visit_number} Prescription</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 32px; color: #122033; }
            h1, h2, h3, p { margin: 0 0 12px; }
            .sheet { display: grid; gap: 20px; }
            .row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
            .card { border: 1px solid #d6e2ef; border-radius: 16px; padding: 18px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border-bottom: 1px solid #d6e2ef; padding: 12px 10px; text-align: left; vertical-align: top; }
            .muted { color: #5b6b7d; }
            .badge { display: inline-block; padding: 6px 10px; border-radius: 999px; background: #eff6ff; color: #1d4ed8; font-weight: 600; font-size: 12px; }
          </style>
        </head>
        <body>
          <div class="sheet">
            <div>
              <span class="badge">E-Prescription</span>
              <h1>${visit.visit_number}</h1>
              <p class="muted">Generated on ${new Date().toLocaleString()}</p>
            </div>
            <div class="row">
              <div class="card">
                <h3>Patient</h3>
                <p><strong>${visit.patient.first_name} ${visit.patient.last_name}</strong></p>
                <p>Patient No: ${visit.patient.patient_number}</p>
                <p>Phone: ${visit.patient.phone ?? '-'}</p>
                <p>Gender: ${visit.patient.gender ?? '-'}</p>
              </div>
              <div class="card">
                <h3>Consultation</h3>
                <p>Doctor: ${visit.consulting_doctor_name}</p>
                <p>Date: ${visit.visit_date}</p>
                <p>Department: ${visit.department_name}</p>
                <p>Chief Complaint: ${visit.chief_complaint || '-'}</p>
                <p>Vitals: ${visit.vital_signs || '-'}</p>
                <p>Diagnosis: ${visit.final_diagnosis || visit.provisional_diagnosis || '-'}</p>
                <p>Follow Up: ${visit.follow_up_date || '-'}</p>
              </div>
            </div>
            <div class="card">
              <h3>Medication Plan</h3>
              <table>
                <thead>
                  <tr>
                    <th>Medicine</th>
                    <th>Qty</th>
                    <th>Instructions</th>
                  </tr>
                </thead>
                <tbody>
                  ${prescriptionOrders
                    .map(
                      (order) => `
                        <tr>
                          <td>${order.item_name}</td>
                          <td>${order.quantity}</td>
                          <td>${order.instructions || '-'}</td>
                        </tr>`
                    )
                    .join('')}
                </tbody>
              </table>
            </div>
            <div class="card">
              <h3>Clinical Note</h3>
              <p>HPI: ${visit.history_of_present_illness || '-'}</p>
              <p>Past History: ${visit.past_history || '-'}</p>
              <p>Examination: ${visit.examination_note || '-'}</p>
              <p>Advice: ${visit.follow_up_note || '-'}</p>
              <p>Note: ${visit.note || 'No additional note recorded.'}</p>
            </div>
          </div>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
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

  private buildDefaultFollowUpDateTime(followUpDate: string): string {
    if (!followUpDate) {
      return '';
    }
    return `${followUpDate}T10:00`;
  }
}
