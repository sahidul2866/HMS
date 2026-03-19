import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { AdminUser, CreateUserPayload } from '../models/admin.models';

@Injectable({ providedIn: 'root' })
export class AdminUserService extends ApiBaseService {
  list(): Observable<AdminUser[]> {
    return this.http.get<AdminUser[]>(this.url('/admin/users'));
  }

  create(payload: CreateUserPayload): Observable<AdminUser> {
    return this.http.post<AdminUser>(this.url('/admin/users'), payload);
  }
}
