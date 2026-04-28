import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { AccountingJournal, CreateJournalPayload } from '../models/accounting.models';

@Injectable({ providedIn: 'root' })
export class AccountingService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  list(): Observable<AccountingJournal[]> {
    return this.cache.get('accounting:journals', () => this.http.get<AccountingJournal[]>(this.url('/accounting/journals')));
  }

  post(payload: CreateJournalPayload): Observable<AccountingJournal> {
    return this.http.post<AccountingJournal>(this.url('/accounting/journal/post'), payload).pipe(tap(() => this.cache.clearPrefix('accounting:')));
  }
}
