import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { User } from '../models/auth.models';
import { ApiBaseService } from './api-base.service';

@Injectable({ providedIn: 'root' })
export class DoctorDirectoryService extends ApiBaseService {
  listDoctors(referralOnly = false): Observable<User[]> {
    return this.http.get<User[]>(this.url(`/users/doctors?referral_only=${referralOnly}`));
  }
}
