import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';

import { User } from '../models/auth.models';
import { ApiBaseService } from './api-base.service';
import { ApiCacheService } from './api-cache.service';
import { SessionService } from './session.service';

// Same any-of gate as GET /users/doctors; without it the server would only answer 403.
const DOCTOR_LIST_PERMISSIONS = ['billing.view', 'opd.view', 'ipd.view', 'settings.user.manage'];

@Injectable({ providedIn: 'root' })
export class DoctorDirectoryService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private readonly session = inject(SessionService);

  listDoctors(referralOnly = false): Observable<User[]> {
    if (!this.session.hasAnyPermission(DOCTOR_LIST_PERMISSIONS)) return of([]);
    return this.cache.getPersistent(`users:doctors:${referralOnly}`, () => this.http.get<User[]>(this.url(`/users/doctors?referral_only=${referralOnly}`)));
  }

  clearCache(): void {
    this.cache.clearPrefix('users:doctors');
  }
}
