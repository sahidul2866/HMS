import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { AdminUser } from '../../../admin/models/admin.models';
import { AdminUserService } from '../../../admin/services/admin-user.service';

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
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  doctors: AdminUser[] = [];
  loading = false;
  saving = false;
  selectedDoctorId = '';
  editorOpen = false;
  activeConfigType: 'fee' | 'header' = 'fee';

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

  openEditor(configType: 'fee' | 'header', doctorId: string): void {
    this.activeConfigType = configType;
    this.selectedDoctorId = doctorId;
    this.syncSelectedDoctor();
    this.editorOpen = true;
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

  onDoctorSelectionChanged(doctorId: string): void {
    this.selectedDoctorId = doctorId;
    this.syncSelectedDoctor();
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

  getConfigRows(): Array<{ key: 'fee' | 'header'; label: string; description: string }> {
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
    ];
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
