import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { AdminUser, AdminRole } from '../../models/admin.models';
import { AdminUserService } from '../../services/admin-user.service';
import { RoleService } from '../../services/role.service';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './user-management.component.html',
  styleUrls: ['./user-management.component.scss'],
})
export class UserManagementComponent {
  private readonly fb = inject(FormBuilder);
  private readonly adminUserService = inject(AdminUserService);
  private readonly roleService = inject(RoleService);
  private readonly patientService = inject(PatientService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  users: AdminUser[] = [];
  roles: AdminRole[] = [];
  patients: Patient[] = [];
  createModalOpen = false;
  creating = false;

  readonly filterForm = this.fb.group({
    query: [''],
    role_code: ['ALL'],
    account_type: ['ALL'],
  });

  readonly form = this.fb.group({
    username: ['', Validators.required],
    email: ['', Validators.required],
    full_name: ['', Validators.required],
    password: ['ChangeMe123!', Validators.required],
    role_code: ['ADMIN', Validators.required],
    patient_id: [''],
  });

  constructor() {
    this.loadRoles();
    this.loadUsers();
    this.loadPatients();
  }

  loadRoles(): void {
    this.roleService.list().subscribe((roles) => (this.roles = roles));
  }

  loadUsers(): void {
    this.adminUserService.list().subscribe((users) => (this.users = users));
  }

  loadPatients(): void {
    this.patientService.list().subscribe((patients) => (this.patients = patients));
  }

  openCreateModal(): void {
    this.createModalOpen = true;
  }

  closeCreateModal(): void {
    this.createModalOpen = false;
    this.form.reset({ password: 'ChangeMe123!', role_code: 'ADMIN', patient_id: '' });
  }

  openOPDSettingsModal(user: AdminUser): void {
    void this.router.navigate(['/opd/settings'], { queryParams: { doctor: user.id } });
  }

  get selectedRoleCode(): string {
    return this.form.controls.role_code.value ?? 'ADMIN';
  }

  get totalUsers(): number {
    return this.users.length;
  }

  get activeUsers(): number {
    return this.users.filter((user) => user.is_active).length;
  }

  get portalUsers(): number {
    return this.users.filter((user) => !!user.patient_id).length;
  }

  get doctorUsers(): number {
    return this.users.filter((user) => user.roles.some((role) => role.is_doctor_role)).length;
  }

  get referralDoctorUsers(): number {
    return this.users.filter((user) => user.roles.some((role) => !!role.is_referral_role)).length;
  }

  get filteredUsers(): AdminUser[] {
    const query = (this.filterForm.controls.query.value ?? '').trim().toLowerCase();
    const roleCode = this.filterForm.controls.role_code.value ?? 'ALL';
    const accountType = this.filterForm.controls.account_type.value ?? 'ALL';

    return this.users.filter((user) => {
      const matchesQuery =
        !query ||
        user.full_name.toLowerCase().includes(query) ||
        user.username.toLowerCase().includes(query) ||
        user.email.toLowerCase().includes(query);
      const matchesRole = roleCode === 'ALL' || user.roles.some((role) => role.code === roleCode);
      const matchesType =
        accountType === 'ALL' ||
        (accountType === 'PORTAL' && !!user.patient_id) ||
        (accountType === 'DOCTOR' && this.isDoctorUser(user)) ||
        (accountType === 'REFERRAL' && this.isReferralDoctorUser(user)) ||
        (accountType === 'STAFF' && !user.patient_id);

      return matchesQuery && matchesRole && matchesType;
    });
  }

  getRoleCodes(user: AdminUser): string {
    return user.roles.map((role) => role.code).join(', ');
  }

  getRoleSummary(user: AdminUser): string {
    if (!user.roles.length) {
      return 'No assigned role';
    }
    return user.roles.map((role) => role.name).join(', ');
  }

  isDoctorUser(user: AdminUser): boolean {
    return user.roles.some((role) => !!role.is_doctor_role);
  }

  isReferralDoctorUser(user: AdminUser): boolean {
    return user.roles.some((role) => !!role.is_referral_role);
  }

  getPatientLabel(patientId: string | null | undefined): string {
    if (!patientId) {
      return 'Not linked to a patient profile';
    }
    const patient = this.patients.find((item) => item.id === patientId);
    return patient ? `${patient.patient_number} · ${patient.first_name} ${patient.last_name}` : 'Patient record linked';
  }

  getInitials(fullName: string): string {
    return fullName
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('');
  }

  isPatientRoleSelected(): boolean {
    return this.selectedRoleCode === 'PATIENT';
  }

  getDoctorFee(user: AdminUser): string {
    return Number(user.opd_consultation_fee ?? 0).toFixed(2);
  }

  getDoctorFollowUpFee(user: AdminUser): string {
    return Number(user.opd_follow_up_fee ?? 0).toFixed(2);
  }

  getOPDHeaderTitle(user: AdminUser): string {
    return user.opd_prescription_header_name?.trim() || user.full_name || 'Header not configured';
  }

  getOPDHeaderMeta(user: AdminUser): string {
    const parts = [
      user.opd_prescription_header_degrees?.trim(),
      user.opd_prescription_header_specialty?.trim(),
      user.opd_prescription_header_workplace?.trim(),
    ].filter(Boolean);
    return parts.length ? parts.join(' • ') : 'Header details not configured';
  }

  resetFilters(): void {
    this.filterForm.reset({ query: '', role_code: 'ALL', account_type: 'ALL' });
  }

  submit(): void {
    if (this.form.invalid || this.creating) {
      return;
    }
    const value = this.form.getRawValue();
    this.creating = true;
    this.adminUserService
      .create({
        username: value.username!,
        email: value.email!,
        full_name: value.full_name!,
        password: value.password!,
        role_codes: [value.role_code!],
        direct_permission_codes: [],
        patient_id: value.patient_id || null,
        is_active: true,
        opd_consultation_fee: 0,
      })
      .subscribe({
        next: () => {
          this.creating = false;
          this.loadUsers();
          this.closeCreateModal();
          this.notificationService.success('User created successfully.');
        },
        error: () => {
          this.creating = false;
        },
      });
  }

}
