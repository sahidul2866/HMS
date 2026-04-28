import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { AdminUser, CreateUserPayload, UpdateUserOPDSettingsPayload } from '../models/admin.models';

@Injectable({ providedIn: 'root' })
export class AdminUserService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  list(): Observable<AdminUser[]> {
    return this.cache.get('admin:users', () => this.http.get<AdminUser[]>(this.url('/admin/users')));
  }

  listDoctors(): Observable<AdminUser[]> {
    return this.cache.get('admin:doctors', () => this.http.get<AdminUser[]>(this.url('/users/doctors')));
  }

  create(payload: CreateUserPayload): Observable<AdminUser> {
    return this.http.post<AdminUser>(this.url('/admin/users'), payload).pipe(tap(() => this.clearCache()));
  }

  updateOPDSettings(userId: string, payload: UpdateUserOPDSettingsPayload): Observable<AdminUser> {
    return this.http.put<AdminUser>(this.url(`/admin/users/${userId}/opd-settings`), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('admin:');
    this.cache.clearPrefix('users:doctors');
  }
}
