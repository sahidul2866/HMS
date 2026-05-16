import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { DataSyncService } from '../../../core/services/data-sync.service';
import { AdminUser, CreateUserPayload, EffectiveAccess, ScopeAssignment, ScopeAssignmentPayload, UpdateUserOPDSettingsPayload } from '../models/admin.models';

@Injectable({ providedIn: 'root' })
export class AdminUserService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly dataSync = inject(DataSyncService);

  list(): Observable<AdminUser[]> {
    return this.cache.get('admin:users', () => this.http.get<AdminUser[]>(this.url('/admin/users')));
  }

  listDoctors(): Observable<AdminUser[]> {
    return this.cache.get('admin:doctors', () => this.http.get<AdminUser[]>(this.url('/users/doctors')));
  }

  create(payload: CreateUserPayload): Observable<AdminUser> {
    return this.http.post<AdminUser>(this.url('/admin/users'), payload).pipe(
      tap((user) => {
        this.clearCache();
        this.publishUserEvent(user.id, 'User list updated.');
      })
    );
  }

  updateOPDSettings(userId: string, payload: UpdateUserOPDSettingsPayload): Observable<AdminUser> {
    return this.http.put<AdminUser>(this.url(`/admin/users/${userId}/opd-settings`), payload).pipe(
      tap((user) => {
        this.clearCache();
        this.publishUserEvent(user.id, 'Doctor settings updated.');
      })
    );
  }

  effectiveAccess(userId: string): Observable<EffectiveAccess> {
    return this.http.get<EffectiveAccess>(this.url(`/admin/users/${userId}/effective-access`));
  }

  listUserScopes(userId: string): Observable<ScopeAssignment[]> {
    return this.http.get<ScopeAssignment[]>(this.url('/admin/scopes/users'), { params: { user_id: userId } });
  }

  createUserScope(payload: ScopeAssignmentPayload): Observable<ScopeAssignment> {
    return this.http.post<ScopeAssignment>(this.url('/admin/scopes/users'), payload).pipe(tap(() => this.clearCache()));
  }

  clearCache(): void {
    this.cache.clearPrefix('admin:');
    this.cache.clearPrefix('users:doctors');
  }

  private publishUserEvent(userId: string | null, message: string): void {
    this.dataSync.publish({
      name: 'user.permission.updated',
      entityType: 'user',
      entityId: userId,
      modules: ['admin', 'appointments', 'opd', 'ipd', 'er', 'billing', 'dashboard'],
      cachePrefixes: ['admin:', 'users:', 'appointments:', 'opd:', 'ipd:', 'er:', 'billing:', 'dashboard:'],
      message,
    });
  }
}
