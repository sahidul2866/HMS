import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import { AdminRole, ScopeAssignment, ScopeAssignmentPayload } from '../models/admin.models';
import { Permission } from '../../../core/models/auth.models';
import { CreateRolePayload } from '../models/admin.models';

@Injectable({ providedIn: 'root' })
export class RoleService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  list(): Observable<AdminRole[]> {
    return this.cache.get('admin:roles', () => this.http.get<AdminRole[]>(this.url('/admin/roles')));
  }

  create(payload: CreateRolePayload): Observable<AdminRole> {
    return this.http.post<AdminRole>(this.url('/admin/roles'), payload).pipe(
      tap((role) => {
        this.clearCache();
        this.publishPermissionEvent(role.code, 'Role permissions updated.');
      })
    );
  }

  updatePermissions(code: string, permission_codes: string[]): Observable<AdminRole> {
    return this.http.put<AdminRole>(this.url(`/admin/roles/${code}/permissions`), { permission_codes }).pipe(
      tap((role) => {
        this.clearCache();
        this.publishPermissionEvent(role.code, 'Permissions updated.');
      })
    );
  }

  listPermissions(): Observable<Permission[]> {
    return this.cache.get('admin:permissions', () => this.http.get<Permission[]>(this.url('/permissions')));
  }

  listRoleScopes(roleId?: string): Observable<ScopeAssignment[]> {
    const options = roleId ? { params: { role_id: roleId } } : {};
    return this.http.get<ScopeAssignment[]>(this.url('/admin/scopes/roles'), options);
  }

  createRoleScope(payload: ScopeAssignmentPayload): Observable<ScopeAssignment> {
    return this.http.post<ScopeAssignment>(this.url('/admin/scopes/roles'), payload).pipe(
      tap(() => {
        this.clearCache();
        this.publishPermissionEvent(payload.role_id || null, 'Role scope updated.');
      })
    );
  }

  deactivateRoleScope(scopeId: string): Observable<ScopeAssignment> {
    return this.http.delete<ScopeAssignment>(this.url(`/admin/scopes/roles/${scopeId}`)).pipe(
      tap(() => {
        this.clearCache();
        this.publishPermissionEvent(scopeId, 'Role scope updated.');
      })
    );
  }

  clearCache(): void {
    this.cache.clearPrefix('admin:roles');
    this.cache.clear('admin:permissions');
  }

  private publishPermissionEvent(roleCode: string | null, message: string): void {
    this.dataSync.publish({
      name: 'user.permission.updated',
      entityType: 'role',
      entityId: roleCode,
      modules: ['admin', 'appointments', 'opd', 'ipd', 'er', 'billing', 'inventory', 'laboratory', 'radiology', 'dashboard'],
      cachePrefixes: ['admin:', 'auth:', 'appointments:', 'opd:', 'ipd:', 'er:', 'billing:', 'inventory:', 'laboratory:', 'radiology:', 'dashboard:'],
      message,
    });
  }
}
