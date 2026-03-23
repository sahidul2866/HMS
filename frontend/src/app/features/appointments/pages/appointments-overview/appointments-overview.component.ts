import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { Appointment } from '../../models/appointment.models';
import { AppointmentsService } from '../../services/appointments.service';

@Component({
  selector: 'app-appointments-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './appointments-overview.component.html',
})
export class AppointmentsOverviewComponent {
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly notificationService = inject(NotificationService);
  private readonly fb = inject(FormBuilder);
  readonly sessionService = inject(SessionService);

  appointments: Appointment[] = [];
  selectedAppointment: Appointment | null = null;

  readonly checkInForm = this.fb.group({
    department_name: ['General OPD', Validators.required],
    consultation_fee: [0, Validators.required],
    chief_complaint: [''],
    note: [''],
  });

  constructor() {
    this.loadAppointments();
  }

  loadAppointments(): void {
    this.appointmentsService.list().subscribe((appointments) => {
      this.appointments = appointments;
      if (this.selectedAppointment) {
        this.selectedAppointment = appointments.find((item) => item.id === this.selectedAppointment?.id) ?? null;
      }
    });
  }

  selectAppointment(appointment: Appointment): void {
    this.selectedAppointment = appointment;
    this.checkInForm.patchValue({
      department_name: 'General OPD',
      consultation_fee: 0,
      chief_complaint: appointment.reason || '',
      note: appointment.note || '',
    });
  }

  updateStatus(appointment: Appointment, status: string): void {
    this.appointmentsService.updateStatus(appointment.id, { status }).subscribe((updated) => {
      this.notificationService.success(`Appointment ${updated.appointment_number} moved to ${status}.`);
      this.loadAppointments();
    });
  }

  checkIn(): void {
    if (!this.selectedAppointment || this.checkInForm.invalid) {
      return;
    }
    this.appointmentsService.checkIn(this.selectedAppointment.id, this.checkInForm.getRawValue() as never).subscribe((visit) => {
      this.notificationService.success(`Checked in to OPD visit ${visit.visit_number}.`);
      this.loadAppointments();
    });
  }

  get todayCount(): number {
    const today = new Date().toISOString().slice(0, 10);
    return this.appointments.filter((item) => item.appointment_at.slice(0, 10) === today).length;
  }

  get scheduledCount(): number {
    return this.appointments.filter((item) => item.status === 'scheduled').length;
  }

  get confirmedCount(): number {
    return this.appointments.filter((item) => item.status === 'confirmed').length;
  }

  get checkedInCount(): number {
    return this.appointments.filter((item) => item.status === 'checked_in').length;
  }
}
