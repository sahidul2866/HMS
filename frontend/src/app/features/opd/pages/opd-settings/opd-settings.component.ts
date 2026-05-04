import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';

import { NotificationService } from '../../../../core/services/notification.service';
import { AppointmentsService } from '../../../appointments/services/appointments.service';
import { AdminUser } from '../../../admin/models/admin.models';
import { AdminUserService } from '../../../admin/services/admin-user.service';

type OPDConfigType = 'fee' | 'header' | 'slot';

interface DoctorSchedule {
  id: string;
  doctor_user_id: string;
  weekday: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  buffer_minutes: number;
}

@Component({
  selector: 'app-opd-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './opd-settings.component.html',
  styleUrls: ['./opd-settings.component.scss'],
})
export class OPDSettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly adminUserService = inject(AdminUserService);
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  doctors: AdminUser[] = [];
  loading = false;
  saving = false;
  selectedDoctorId = '';
  editorOpen = false;
  activeConfigType: OPDConfigType = 'fee';
  scheduleSaving = false;
  doctorSchedules: DoctorSchedule[] = [];

  readonly settingsForm = this.fb.group({
    opd_consultation_fee: [0, [Validators.required]],
    opd_follow_up_fee: [0, [Validators.required]],
    opd_follow_up_days: [30, [Validators.required, Validators.min(1)]],
    opd_prescription_header_name: [''],
    opd_prescription_header_degrees: [''],
    opd_prescription_header_specialty: [''],
    opd_prescription_header_workplace: [''],
    opd_prescription_header_chamber: [''],
    opd_prescription_header_phone: [''],
    opd_prescription_header_address: [''],
  });

  readonly slotForm = this.fb.group({
    weekdays: this.fb.nonNullable.control<number[]>([0], [Validators.required]),
    start_time: ['09:00', [Validators.required]],
    end_time: ['17:00', [Validators.required]],
    slot_duration_minutes: [15, [Validators.required, Validators.min(5), Validators.max(180)]],
    buffer_minutes: [0, [Validators.required, Validators.min(0), Validators.max(60)]],
  });

  constructor() {
    this.loadDoctors();
    this.route.queryParamMap.subscribe((params) => {
      const doctorId = params.get('doctor');
      if (doctorId) {
        this.selectedDoctorId = doctorId;
        if (this.doctors.length) {
          this.syncSelectedDoctor();
          this.editorOpen = true;
        }
      }
    });
  }

  loadDoctors(): void {
    this.loading = true;
    this.adminUserService.listDoctors().subscribe({
      next: (doctors) => {
        this.doctors = doctors;
        if (!this.selectedDoctorId && doctors.length) {
          this.selectedDoctorId = doctors[0].id;
        }
        if (this.selectedDoctorId && this.editorOpen) {
          this.syncSelectedDoctor();
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  get selectedDoctor(): AdminUser | null {
    return this.doctors.find((doctor) => doctor.id === this.selectedDoctorId) ?? null;
  }

  openEditor(configType: OPDConfigType, doctorId: string): void {
    this.activeConfigType = configType;
    this.selectedDoctorId = doctorId;
    this.syncSelectedDoctor();
    this.editorOpen = true;
    if (configType === 'slot') {
      this.loadDoctorSchedules();
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { doctor: doctorId || null },
      queryParamsHandling: 'merge',
    });
  }

  closeEditor(): void {
    this.editorOpen = false;
  }

  get isFeeEditor(): boolean {
    return this.activeConfigType === 'fee';
  }

  get isHeaderEditor(): boolean {
    return this.activeConfigType === 'header';
  }

  get isSlotEditor(): boolean {
    return this.activeConfigType === 'slot';
  }

  onDoctorSelectionChanged(doctorId: string): void {
    this.selectedDoctorId = doctorId;
    this.syncSelectedDoctor();
    if (this.isSlotEditor) {
      this.loadDoctorSchedules();
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { doctor: doctorId || null },
      queryParamsHandling: 'merge',
    });
  }

  saveSettings(): void {
    if (!this.selectedDoctor || this.settingsForm.invalid || this.saving) {
      return;
    }

    this.saving = true;
    const raw = this.settingsForm.getRawValue();
    this.adminUserService.updateOPDSettings(this.selectedDoctor.id, {
      opd_consultation_fee: Number(raw.opd_consultation_fee ?? 0),
      opd_follow_up_fee: Number(raw.opd_follow_up_fee ?? 0),
      opd_follow_up_days: Number(raw.opd_follow_up_days ?? 30),
      opd_prescription_header_name: raw.opd_prescription_header_name?.trim() || null,
      opd_prescription_header_degrees: raw.opd_prescription_header_degrees?.trim() || null,
      opd_prescription_header_specialty: raw.opd_prescription_header_specialty?.trim() || null,
      opd_prescription_header_workplace: raw.opd_prescription_header_workplace?.trim() || null,
      opd_prescription_header_chamber: raw.opd_prescription_header_chamber?.trim() || null,
      opd_prescription_header_phone: raw.opd_prescription_header_phone?.trim() || null,
      opd_prescription_header_address: raw.opd_prescription_header_address?.trim() || null,
    }).subscribe({
      next: (updatedDoctor) => {
        this.saving = false;
        this.doctors = this.doctors.map((doctor) => doctor.id === updatedDoctor.id ? updatedDoctor : doctor);
        this.selectedDoctorId = updatedDoctor.id;
        this.syncSelectedDoctor();
        this.editorOpen = false;
        this.notificationService.success(`OPD settings updated for ${updatedDoctor.full_name}.`);
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  saveSlotSettings(): void {
    if (!this.selectedDoctor || this.slotForm.invalid || this.scheduleSaving) {
      return;
    }
    const raw = this.slotForm.getRawValue();
    const weekdays = (raw.weekdays ?? []).map((item) => Number(item)).filter((item) => item >= 0 && item <= 6);
    if (!weekdays.length) {
      this.notificationService.warning('Select at least one weekday.');
      return;
    }
    this.scheduleSaving = true;
    const requests = weekdays.map((weekday) =>
      this.appointmentsService.upsertDoctorSchedule({
        doctor_user_id: this.selectedDoctor!.id,
        weekday,
        start_time: raw.start_time || '09:00',
        end_time: raw.end_time || '17:00',
        slot_duration_minutes: Number(raw.slot_duration_minutes ?? 15),
        buffer_minutes: Number(raw.buffer_minutes ?? 0),
      })
    );
    forkJoin(requests)
      .subscribe({
        next: () => {
          this.scheduleSaving = false;
          this.notificationService.success('Doctor slot schedule saved for selected days.');
          this.loadDoctorSchedules();
        },
        error: () => {
          this.scheduleSaving = false;
        },
      });
  }

  editSchedule(schedule: DoctorSchedule): void {
    this.slotForm.patchValue({
      weekdays: [schedule.weekday],
      start_time: schedule.start_time,
      end_time: schedule.end_time,
      slot_duration_minutes: schedule.slot_duration_minutes,
      buffer_minutes: schedule.buffer_minutes,
    });
  }

  isWeekdaySelected(value: number): boolean {
    return (this.slotForm.controls.weekdays.value ?? []).includes(value);
  }

  toggleWeekday(value: number): void {
    const current = this.slotForm.controls.weekdays.value ?? [];
    const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
    this.slotForm.controls.weekdays.setValue(next);
    this.slotForm.controls.weekdays.markAsDirty();
    this.slotForm.controls.weekdays.markAsTouched();
  }

  weekdayLabel(value: number): string {
    const labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return labels[value] ?? '-';
  }

  getDoctorFee(user: AdminUser): string {
    const consultation = Number(user.opd_consultation_fee ?? 0).toFixed(2);
    const followUp = Number(user.opd_follow_up_fee ?? 0).toFixed(2);
    const days = Number(user.opd_follow_up_days ?? 30);
    return `${consultation} / ${followUp} (${days}d)`;
  }

  getHeaderSummary(user: AdminUser): string {
    const parts = [
      user.opd_prescription_header_name?.trim() || user.full_name,
      user.opd_prescription_header_specialty?.trim(),
      user.opd_prescription_header_phone?.trim(),
    ].filter(Boolean);
    return parts.join(' • ');
  }

  getHeaderList(user: AdminUser): Array<{ label: string; value: string }> {
    return [
      { label: 'Header Name', value: user.opd_prescription_header_name?.trim() || user.full_name || '-' },
      { label: 'Degrees', value: user.opd_prescription_header_degrees?.trim() || '-' },
      { label: 'Specialty', value: user.opd_prescription_header_specialty?.trim() || '-' },
      { label: 'Workplace', value: user.opd_prescription_header_workplace?.trim() || '-' },
      { label: 'Chamber', value: user.opd_prescription_header_chamber?.trim() || '-' },
      { label: 'Phone', value: user.opd_prescription_header_phone?.trim() || '-' },
      { label: 'Address', value: user.opd_prescription_header_address?.trim() || '-' },
    ];
  }

  getConfigRows(): Array<{ key: OPDConfigType; label: string; description: string }> {
    return [
      {
        key: 'fee',
        label: 'Fee Related Settings',
        description: 'Consultation fee, follow-up fee, and follow-up days used during OPD registration and billing.',
      },
      {
        key: 'header',
        label: 'Prescription Header Settings',
        description: 'Doctor header name, credentials, specialty, workplace, chamber, phone, and address for printed prescriptions.',
      },
      {
        key: 'slot',
        label: 'Doctor Slot Schedule',
        description: 'Weekday-wise OPD slot configuration used for appointment and OPD visit booking.',
      },
    ];
  }

  private loadDoctorSchedules(): void {
    if (!this.selectedDoctor) {
      this.doctorSchedules = [];
      return;
    }
    this.appointmentsService.listDoctorSchedules(this.selectedDoctor.id).subscribe({
      next: (schedules) => {
        this.doctorSchedules = [...schedules].sort((a, b) => a.weekday - b.weekday);
      },
      error: () => {
        this.doctorSchedules = [];
      },
    });
  }

  private syncSelectedDoctor(): void {
    if (!this.selectedDoctor) {
      return;
    }
    const doctor = this.selectedDoctor;
    this.settingsForm.reset({
      opd_consultation_fee: Number(doctor.opd_consultation_fee ?? 0),
      opd_follow_up_fee: Number(doctor.opd_follow_up_fee ?? 0),
      opd_follow_up_days: Number(doctor.opd_follow_up_days ?? 30),
      opd_prescription_header_name: doctor.opd_prescription_header_name ?? doctor.full_name ?? '',
      opd_prescription_header_degrees: doctor.opd_prescription_header_degrees ?? '',
      opd_prescription_header_specialty: doctor.opd_prescription_header_specialty ?? '',
      opd_prescription_header_workplace: doctor.opd_prescription_header_workplace ?? '',
      opd_prescription_header_chamber: doctor.opd_prescription_header_chamber ?? '',
      opd_prescription_header_phone: doctor.opd_prescription_header_phone ?? '',
      opd_prescription_header_address: doctor.opd_prescription_header_address ?? '',
    });
  }
}
