import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { Permission } from '../../../../core/models/auth.models';
import { AdminRole } from '../../models/admin.models';
import { RoleService } from '../../services/role.service';

@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './role-management.component.html',
})
export class RoleManagementComponent {
  private readonly roleService = inject(RoleService);

  roles: AdminRole[] = [];
  permissions: Permission[] = [];
  selectedRoleCode = '';
  selectedPermissionCodes = new Set<string>();

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
    this.selectedPermissionCodes = new Set(role?.permissions.map((item) => item.code) ?? []);
  }

  isSelected(code: string): boolean {
    return this.selectedPermissionCodes.has(code);
  }

  togglePermission(code: string, checked: boolean): void {
    if (checked) {
      this.selectedPermissionCodes.add(code);
      return;
    }
    this.selectedPermissionCodes.delete(code);
  }

  getSelectedPermissionCount(role: AdminRole): number {
    return role.permissions.length;
  }

  save(): void {
    if (!this.selectedRoleCode) {
      return;
    }
    const codes = Array.from(this.selectedPermissionCodes.values()).sort();
    this.roleService.updatePermissions(this.selectedRoleCode, codes).subscribe(() => this.reload());
  }
}
