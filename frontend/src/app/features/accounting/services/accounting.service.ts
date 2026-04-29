import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import {
  Account,
  AccountingDashboard,
  AccountingJournal,
  AccountingWorkspace,
  CreateJournalPayload,
  FinanceRecord,
  JournalEntry,
} from '../models/accounting.models';

@Injectable({ providedIn: 'root' })
export class AccountingService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  dashboard(): Observable<AccountingDashboard> {
    return this.cache.get('accounting:dashboard', () => this.http.get<AccountingDashboard>(this.url('/accounting/dashboard')));
  }

  workspace(): Observable<AccountingWorkspace> {
    return this.cache.get('accounting:workspace', () => this.http.get<AccountingWorkspace>(this.url('/accounting/workspace')));
  }

  accounts(): Observable<Account[]> {
    return this.cache.get('accounting:accounts', () => this.http.get<Account[]>(this.url('/accounting/accounts')));
  }

  createAccount(payload: Record<string, unknown>): Observable<Account> {
    return this.http.post<Account>(this.url('/accounting/accounts'), payload).pipe(tap(() => this.clear()));
  }

  journalEntries(): Observable<JournalEntry[]> {
    return this.cache.get('accounting:journal-entries', () => this.http.get<JournalEntry[]>(this.url('/accounting/journal-entries')));
  }

  createJournalEntry(payload: Record<string, unknown>): Observable<JournalEntry> {
    return this.http.post<JournalEntry>(this.url('/accounting/journal-entries'), payload).pipe(tap(() => this.clear()));
  }

  list(): Observable<AccountingJournal[]> {
    return this.cache.get('accounting:journals', () => this.http.get<AccountingJournal[]>(this.url('/accounting/journals')));
  }

  post(payload: CreateJournalPayload): Observable<AccountingJournal> {
    return this.http.post<AccountingJournal>(this.url('/accounting/journal/post'), payload).pipe(tap(() => this.clear()));
  }

  createWorkflow(kind: string, payload: Record<string, unknown>): Observable<FinanceRecord> {
    return this.http.post<FinanceRecord>(this.url(`/accounting/${kind}`), payload).pipe(tap(() => this.clear()));
  }

  clear(): void {
    this.cache.clearPrefix('accounting:');
    this.cache.clearPrefix('dashboard:');
  }
}
