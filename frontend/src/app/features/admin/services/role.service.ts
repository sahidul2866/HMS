import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { AdminRole } from '../models/admin.models';
import { Permission } from '../../../core/models/auth.models';

@Injectable({ providedIn: 'root' })
export class RoleService extends ApiBaseService {
  list(): Observable<AdminRole[]> {
    return this.http.get<AdminRole[]>(this.url('/admin/roles'));
  }

  updatePermissions(code: string, permission_codes: string[]): Observable<AdminRole> {
    return this.http.put<AdminRole>(this.url(`/admin/roles/${code}/permissions`), { permission_codes });
  }

  listPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(this.url('/permissions'));
  }
}
