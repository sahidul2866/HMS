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

  get completedLabReports() {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders.filter((order) => order.service_area === 'laboratory' && order.status === 'completed')
    );
  }

  get completedRadiologyReports() {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders.filter((order) => order.service_area === 'radiology' && order.status === 'completed')
    );
  }
}
