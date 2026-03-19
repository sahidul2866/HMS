import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AdminUserService } from '../../services/admin-user.service';
import { AdminUser } from '../../models/admin.models';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './user-management.component.html',
})
export class UserManagementComponent {
  private readonly fb = inject(FormBuilder);
  private readonly adminUserService = inject(AdminUserService);

  users: AdminUser[] = [];

  readonly form = this.fb.group({
    username: ['', Validators.required],
    email: ['', Validators.required],
    full_name: ['', Validators.required],
    password: ['ChangeMe123!', Validators.required],
    role_codes: ['ADMIN', Validators.required],
  });

  constructor() {
    this.loadUsers();
  }

  loadUsers(): void {
    this.adminUserService.list().subscribe((users) => (this.users = users));
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
        role_codes: value.role_codes!.split(',').map((item) => item.trim()),
        direct_permission_codes: [],
        is_active: true,
      })
      .subscribe(() => {
        this.form.reset({ password: 'ChangeMe123!', role_codes: 'ADMIN' });
        this.loadUsers();
      });
  }
}

