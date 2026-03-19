import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from './api-base.service';
import { User } from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class CurrentUserService extends ApiBaseService {
  getCurrentUser(): Observable<User> {
    return this.http.get<User>(this.url('/auth/me'));
  }
}

