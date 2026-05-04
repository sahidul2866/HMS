import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { Appointment } from '../../models/appointment.models';
import { AppointmentsService } from '../../services/appointments.service';

@Component({
  selector: 'app-appointments-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './appointments-overview.component.html',
  styleUrls: ['./appointments-overview.component.scss'],
})
export class AppointmentsOverviewComponent {
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  readonly sessionService = inject(SessionService);

  appointments: Appointment[] = [];
  doctors: User[] = [];
  selectedDoctorUserId = '';
  selectedStatus = '';
  selectedDate = '';
  searchText = '';
  selectedAppointment: Appointment | null = null;
  sortField: 'number' | 'patient' | 'doctor' | 'time' | 'status' | 'reason' = 'time';
  sortDirection: 'asc' | 'desc' = 'desc';

  readonly checkInForm = this.fb.group({
    department_name: ['General OPD', Validators.required],
    consultation_fee: [0, Validators.required],
    chief_complaint: [''],
    note: [''],
  });

  constructor() {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
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

  navigateToCreateAppointment(): void {
    void this.router.navigate(['/appointments/create']);
  }

  get filteredAppointments(): Appointment[] {
    const search = this.searchText.trim().toLowerCase();
    const filtered = this.appointments.filter((appointment) => {
      const doctorMatch = !this.selectedDoctorUserId || appointment.doctor_user_id === this.selectedDoctorUserId;
      const statusMatch = !this.selectedStatus || appointment.status === this.selectedStatus;
      const dateMatch = !this.selectedDate || appointment.appointment_at.slice(0, 10) === this.selectedDate;
      const searchMatch =
        !search ||
        appointment.appointment_number.toLowerCase().includes(search) ||
        appointment.patient_name.toLowerCase().includes(search) ||
        appointment.doctor_name.toLowerCase().includes(search) ||
        (appointment.reason || '').toLowerCase().includes(search);
      return doctorMatch && statusMatch && dateMatch && searchMatch;
    });
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
      switch (this.sortField) {
        case 'number':
          return dir * a.appointment_number.localeCompare(b.appointment_number);
        case 'patient':
          return dir * a.patient_name.localeCompare(b.patient_name);
        case 'doctor':
          return dir * a.doctor_name.localeCompare(b.doctor_name);
        case 'status':
          return dir * a.status.localeCompare(b.status);
        case 'reason':
          return dir * (a.reason || '').localeCompare(b.reason || '');
        case 'time':
        default:
          return dir * (new Date(a.appointment_at).getTime() - new Date(b.appointment_at).getTime());
      }
    });
  }

  toggleSort(field: AppointmentsOverviewComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'time' ? 'desc' : 'asc';
  }
}
