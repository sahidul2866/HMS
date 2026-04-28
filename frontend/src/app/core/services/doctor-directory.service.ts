import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { User } from '../models/auth.models';
import { ApiBaseService } from './api-base.service';
import { ApiCacheService } from './api-cache.service';

@Injectable({ providedIn: 'root' })
export class DoctorDirectoryService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  listDoctors(referralOnly = false): Observable<User[]> {
    return this.cache.getPersistent(`users:doctors:${referralOnly}`, () => this.http.get<User[]>(this.url(`/users/doctors?referral_only=${referralOnly}`)));
  }

  clearCache(): void {
    this.cache.clearPrefix('users:doctors');
  }
}
