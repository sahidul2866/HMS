import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AdminUser, AdminRole } from '../../models/admin.models';
import { AdminUserService } from '../../services/admin-user.service';
import { RoleService } from '../../services/role.service';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './user-management.component.html',
})
export class UserManagementComponent {
  private readonly fb = inject(FormBuilder);
  private readonly adminUserService = inject(AdminUserService);
  private readonly roleService = inject(RoleService);

  users: AdminUser[] = [];
  roles: AdminRole[] = [];

  readonly form = this.fb.group({
    username: ['', Validators.required],
    email: ['', Validators.required],
    full_name: ['', Validators.required],
    password: ['ChangeMe123!', Validators.required],
    role_code: ['ADMIN', Validators.required],
  });

  constructor() {
    this.loadRoles();
    this.loadUsers();
  }

  loadRoles(): void {
    this.roleService.list().subscribe((roles) => (this.roles = roles));
  }

  loadUsers(): void {
    this.adminUserService.list().subscribe((users) => (this.users = users));
  }

  getRoleCodes(user: AdminUser): string {
    return user.roles.map((role) => role.code).join(', ');
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const value = this.form.getRawValue();
    this.adminUserService
      .create({
        username: value.username!,
        email: value.email!,
        full_name: value.full_name!,
        password: value.password!,
        role_codes: [value.role_code!],
        direct_permission_codes: [],
        is_active: true,
      })
      .subscribe(() => {
        this.form.reset({ password: 'ChangeMe123!', role_code: 'ADMIN' });
        this.loadUsers();
      });
  }
}
