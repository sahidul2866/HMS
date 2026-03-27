import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { User } from '../../../../core/models/auth.models';
import { PatientClinicalHistory } from '../../../patients/models/patient.models';
import { PatientAppointment } from '../../models/patient-portal.models';
import { PatientPortalService } from '../../services/patient-portal.service';

@Component({
  selector: 'app-patient-portal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './patient-portal.component.html',
  styleUrls: ['./patient-portal.component.scss'],
})
export class PatientPortalComponent {
  private readonly portalService = inject(PatientPortalService);
  private readonly notificationService = inject(NotificationService);
  private readonly fb = inject(FormBuilder);

  history: PatientClinicalHistory | null = null;
  appointments: PatientAppointment[] = [];
  doctors: User[] = [];

  readonly form = this.fb.group({
    doctor_user_id: ['', Validators.required],
    appointment_at: ['', Validators.required],
    reason: ['', Validators.required],
    note: [''],
  });

  constructor() {
    this.loadPortal();
  }

  loadPortal(): void {
    this.portalService.getOverview().subscribe((overview) => {
      this.history = overview.patient;
      this.appointments = overview.appointments;
      this.doctors = overview.doctors;
    });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    this.portalService.bookAppointment(this.form.getRawValue() as never).subscribe((appointment) => {
      this.appointments = [appointment, ...this.appointments];
      this.form.reset({ doctor_user_id: '', appointment_at: '', reason: '', note: '' });
      this.notificationService.success(`Appointment ${appointment.appointment_number} booked.`);
    });
  }

  cancelAppointment(appointment: PatientAppointment): void {
    if (appointment.status !== 'scheduled' && appointment.status !== 'confirmed') {
      return;
    }
    this.portalService.updateAppointmentStatus(appointment.id, { status: 'cancelled' }).subscribe((updated) => {
      this.appointments = this.appointments.map((item) => (item.id === updated.id ? updated : item));
      this.notificationService.warning(`Appointment ${updated.appointment_number} cancelled.`);
    });
  }

  get completedLabReports() {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders.filter((order) => order.service_area === 'laboratory' && ['completed', 'verified'].includes(order.status))
    );
  }

  get completedRadiologyReports() {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders.filter((order) => order.service_area === 'radiology' && ['completed', 'verified'].includes(order.status))
    );
  }

  get prescriptionArchive() {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders
        .filter((order) => order.order_type === 'prescription')
        .map((order) => ({
          visit_number: visit.visit_number,
          visit_date: visit.visit_date,
          doctor_name: visit.consulting_doctor_name,
          diagnosis: visit.final_diagnosis || visit.provisional_diagnosis,
          ...order,
        }))
    );
  }

  get totalOutstandingDue(): number {
    return (this.history?.billing_invoices ?? []).reduce((sum, invoice) => sum + Number(invoice.due_amount || 0), 0);
  }

  get totalPaidAmount(): number {
    return (this.history?.billing_invoices ?? []).reduce((sum, invoice) => sum + Number(invoice.paid_amount || 0), 0);
  }

  get upcomingAppointments(): PatientAppointment[] {
    return this.appointments.filter((item) => ['scheduled', 'confirmed'].includes(item.status));
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value || 0));
  }
}
