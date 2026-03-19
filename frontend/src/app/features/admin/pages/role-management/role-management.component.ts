import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Permission } from '../../../../core/models/auth.models';
import { RoleService } from '../../services/role.service';
import { AdminRole } from '../../models/admin.models';

@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './role-management.component.html',
})
export class RoleManagementComponent {
  private readonly roleService = inject(RoleService);

  roles: AdminRole[] = [];
  permissions: Permission[] = [];
  selectedRoleCode = '';
  permissionCodes = '';

  constructor() {
    this.reload();
  }

  reload(): void {
    this.roleService.list().subscribe((roles) => (this.roles = roles));
    this.roleService.listPermissions().subscribe((permissions) => (this.permissions = permissions));
  }

  loadRole(code: string): void {
    this.selectedRoleCode = code;
    const role = this.roles.find((item) => item.code === code);
    this.permissionCodes = role?.permissions.map((item) => item.code).join(', ') ?? '';
  }

  save(): void {
    if (!this.selectedRoleCode) {
      return;
    }
    const codes = this.permissionCodes
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    this.roleService.updatePermissions(this.selectedRoleCode, codes).subscribe(() => this.reload());
  }
}

