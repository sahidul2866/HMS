import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

import { ApiBaseService } from './api-base.service';
import { ApiCacheService } from './api-cache.service';
import { User } from '../models/auth.models';
import { HttpHeaders } from '@angular/common/http';
import { inject } from '@angular/core';

const SKIP_AUTH_REFRESH_HEADER = 'X-Skip-Auth-Refresh';

@Injectable({ providedIn: 'root' })
export class CurrentUserService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);
  private currentUser$?: Observable<User>;

  getCurrentUser(): Observable<User> {
    return this.currentUser$ ?? this.cache.get('auth:me', () =>
      this.http.get<User>(this.url('/auth/me'), {
        headers: new HttpHeaders({
          [SKIP_AUTH_REFRESH_HEADER]: '1',
        }),
      })
    );
  }

  setCachedUser(user: User): void {
    this.cache.clear('auth:me');
    this.currentUser$ = of(user);
  }

  clearCache(): void {
    this.currentUser$ = undefined;
    this.cache.clear('auth:me');
  }
}
