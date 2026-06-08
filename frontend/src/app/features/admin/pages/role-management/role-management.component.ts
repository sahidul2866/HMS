import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { Permission } from '../../../../core/models/auth.models';
import { NotificationService } from '../../../../core/services/notification.service';
import { AdminRole, ScopeAssignment } from '../../models/admin.models';
import { RoleService } from '../../services/role.service';

interface PermissionGroup {
  module: string;
  label: string;
  permissions: Permission[];
}

@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './role-management.component.html',
  styleUrls: ['./role-management.component.scss'],
})
export class RoleManagementComponent {
  private readonly fb = inject(FormBuilder);
  private readonly roleService = inject(RoleService);
  private readonly notificationService = inject(NotificationService);

  roles: AdminRole[] = [];
  permissions: Permission[] = [];
  permissionGroups: PermissionGroup[] = [];
  selectedRoleCode = '';
  selectedPermissionCodes = new Set<string>();
  selectedRoleScopes: ScopeAssignment[] = [];
  isCreateRoleModalOpen = false;

  readonly createRoleForm = this.fb.group({
    code: ['', [Validators.required, Validators.minLength(3)]],
    name: ['', [Validators.required, Validators.minLength(3)]],
    description: [''],
    is_doctor_role: [false],
    is_referral_role: [false],
  });

  readonly scopeForm = this.fb.group({
    scope_type: ['ward', Validators.required],
    scope_value: ['', Validators.required],
    scope_ref_id: [''],
    module: ['ipd'],
    is_primary: [false],
    starts_at: [''],
    ends_at: [''],
    reason: [''],
  });

  constructor() {
    this.reload();
  }

  reload(): void {
    this.roleService.list().subscribe((roles) => {
      this.roles = [...roles].sort((left, right) => left.code.localeCompare(right.code));
      if (this.selectedRoleCode) {
        const selectedRole = this.roles.find((role) => role.code === this.selectedRoleCode);
        if (selectedRole) {
          this.selectedPermissionCodes = new Set(selectedRole.permissions.map((item) => item.code));
        }
      }
    });

    this.roleService.listPermissions().subscribe((permissions) => {
      this.permissions = [...permissions].sort((left, right) => {
        const moduleCompare = left.module.localeCompare(right.module);
        if (moduleCompare !== 0) {
          return moduleCompare;
        }
        return left.code.localeCompare(right.code);
      });
      this.permissionGroups = this.buildPermissionGroups(this.permissions);
    });
  }

  loadRole(code: string): void {
    this.selectedRoleCode = code;
    const role = this.roles.find((item) => item.code === code);
    this.selectedPermissionCodes = new Set(role?.permissions.map((item) => item.code) ?? []);
    this.loadRoleScopes();
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

  get selectedRole(): AdminRole | undefined {
    return this.roles.find((role) => role.code === this.selectedRoleCode);
  }

  areAllPermissionsSelected(): boolean {
    return this.permissions.length > 0 && this.permissions.every((permission) => this.isSelected(permission.code));
  }

  isPartiallySelected(): boolean {
    const selectedCount = this.permissions.filter((permission) => this.isSelected(permission.code)).length;
    return selectedCount > 0 && selectedCount < this.permissions.length;
  }

  toggleAllPermissions(checked: boolean): void {
    for (const permission of this.permissions) {
      this.togglePermission(permission.code, checked);
    }
  }

  isModuleSelected(group: PermissionGroup): boolean {
    return group.permissions.length > 0 && group.permissions.every((permission) => this.isSelected(permission.code));
  }

  isModulePartiallySelected(group: PermissionGroup): boolean {
    const selectedCount = this.getModuleSelectedCount(group);
    return selectedCount > 0 && selectedCount < group.permissions.length;
  }

  getModuleSelectedCount(group: PermissionGroup): number {
    return group.permissions.filter((permission) => this.isSelected(permission.code)).length;
  }

  toggleModule(group: PermissionGroup, checked: boolean): void {
    for (const permission of group.permissions) {
      this.togglePermission(permission.code, checked);
    }
  }

  submitNewRole(): void {
    if (this.createRoleForm.invalid) {
      this.createRoleForm.markAllAsTouched();
      return;
    }

    const value = this.createRoleForm.getRawValue();
    const code = value.code?.trim().toUpperCase() ?? '';
    const name = value.name?.trim() ?? '';
    const description = value.description?.trim() ?? '';

    this.roleService
      .create({
        code,
        name,
        description: description || null,
        is_doctor_role: !!value.is_doctor_role,
        is_referral_role: !!value.is_referral_role,
        permission_codes: [],
      })
      .subscribe((role) => {
        this.createRoleForm.reset({ code: '', name: '', description: '', is_doctor_role: false, is_referral_role: false });
        this.isCreateRoleModalOpen = false;
        this.notificationService.success(`Role ${role.code} created successfully.`);
        this.reload();
        this.loadRole(role.code);
      });
  }

  openCreateRoleModal(): void {
    this.isCreateRoleModalOpen = true;
  }

  closeCreateRoleModal(): void {
    this.isCreateRoleModalOpen = false;
    this.createRoleForm.reset({ code: '', name: '', description: '', is_doctor_role: false, is_referral_role: false });
  }

  save(): void {
    if (!this.selectedRoleCode) {
      return;
    }
    const codes = Array.from(this.selectedPermissionCodes.values()).sort();
    this.roleService.updatePermissions(this.selectedRoleCode, codes).subscribe(() => {
      this.reload();
      this.notificationService.success(`Permissions updated for ${this.selectedRoleCode}.`);
    });
  }

  loadRoleScopes(): void {
    if (!this.selectedRole?.id) {
      this.selectedRoleScopes = [];
      return;
    }
    this.roleService.listRoleScopes(this.selectedRole.id).subscribe((scopes) => {
      this.selectedRoleScopes = scopes.filter((scope) => scope.is_active);
    });
  }

  submitScope(): void {
    const role = this.selectedRole;
    if (!role || this.scopeForm.invalid) {
      this.scopeForm.markAllAsTouched();
      return;
    }
    const value = this.scopeForm.getRawValue();
    this.roleService
      .createRoleScope({
        role_id: role.id,
        scope_type: value.scope_type!,
        scope_value: value.scope_value || null,
        scope_ref_id: value.scope_ref_id || null,
        module: value.module || null,
        status: 'active',
        is_primary: !!value.is_primary,
        is_temporary: false,
        is_override: false,
        starts_at: value.starts_at || null,
        ends_at: value.ends_at || null,
        reason: value.reason || null,
        meta: {},
      })
      .subscribe(() => {
        this.notificationService.success(`Scope assigned to ${role.code}.`);
        this.scopeForm.patchValue({ scope_value: '', scope_ref_id: '', reason: '' });
        this.loadRoleScopes();
      });
  }

  removeScope(scope: ScopeAssignment): void {
    this.roleService.deactivateRoleScope(scope.id).subscribe(() => {
      this.notificationService.success('Role scope removed.');
      this.loadRoleScopes();
    });
  }

  private buildPermissionGroups(permissions: Permission[]): PermissionGroup[] {
    const groups = new Map<string, Permission[]>();
    for (const permission of permissions) {
      const modulePermissions = groups.get(permission.module) ?? [];
      modulePermissions.push(permission);
      groups.set(permission.module, modulePermissions);
    }

    return Array.from(groups.entries())
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([module, modulePermissions]) => ({
        module,
        label: this.formatModuleLabel(module),
        permissions: modulePermissions,
      }));
  }

  private formatModuleLabel(module: string): string {
    return module
      .split(/[._-]+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }
}
