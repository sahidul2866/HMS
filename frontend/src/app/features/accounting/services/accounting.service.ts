import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { AccountingJournal, CreateJournalPayload } from '../models/accounting.models';

@Injectable({ providedIn: 'root' })
export class AccountingService extends ApiBaseService {
  list(): Observable<AccountingJournal[]> {
    return this.http.get<AccountingJournal[]>(this.url('/accounting/journals'));
  }

  post(payload: CreateJournalPayload): Observable<AccountingJournal> {
    return this.http.post<AccountingJournal>(this.url('/accounting/journal/post'), payload);
  }
}
