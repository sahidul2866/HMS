import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { AdminRole } from '../models/admin.models';
import { Permission } from '../../../core/models/auth.models';
import { CreateRolePayload } from '../models/admin.models';

@Injectable({ providedIn: 'root' })
export class RoleService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  list(): Observable<AdminRole[]> {
    return this.cache.get('admin:roles', () => this.http.get<AdminRole[]>(this.url('/admin/roles')));
  }

  create(payload: CreateRolePayload): Observable<AdminRole> {
    return this.http.post<AdminRole>(this.url('/admin/roles'), payload).pipe(tap(() => this.clearCache()));
  }

  updatePermissions(code: string, permission_codes: string[]): Observable<AdminRole> {
    return this.http.put<AdminRole>(this.url(`/admin/roles/${code}/permissions`), { permission_codes }).pipe(tap(() => this.clearCache()));
  }

  listPermissions(): Observable<Permission[]> {
    return this.cache.get('admin:permissions', () => this.http.get<Permission[]>(this.url('/permissions')));
  }

  clearCache(): void {
    this.cache.clearPrefix('admin:roles');
    this.cache.clear('admin:permissions');
  }
}
