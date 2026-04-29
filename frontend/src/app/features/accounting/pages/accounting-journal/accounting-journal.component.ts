import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { AccountingDashboard, AccountingWorkspace, ChartPoint, FinanceRecord } from '../../models/accounting.models';
import { AccountingService } from '../../services/accounting.service';

type AccountingTab = 'dashboard' | 'accounts' | 'collections' | 'receivables' | 'payables' | 'expenses' | 'payroll' | 'doctor' | 'cash' | 'bank' | 'journals' | 'reports' | 'audit';

@Component({
  selector: 'app-accounting-journal',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './accounting-journal.component.html',
  styleUrls: ['./accounting-journal.component.scss'],
})
export class AccountingJournalComponent {
  private readonly accountingService = inject(AccountingService);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly tab = signal<AccountingTab>('dashboard');
  readonly tabs: { key: AccountingTab; label: string; route: string }[] = [
    { key: 'dashboard', label: 'Dashboard', route: '/accounting' },
    { key: 'accounts', label: 'Accounts', route: '/accounting/accounts' },
    { key: 'collections', label: 'Collection', route: '/accounting/collections' },
    { key: 'receivables', label: 'Receivables', route: '/accounting/receivables' },
    { key: 'payables', label: 'Payables', route: '/accounting/payables' },
    { key: 'expenses', label: 'Expenses', route: '/accounting/expenses' },
    { key: 'payroll', label: 'Payroll', route: '/accounting/payroll' },
    { key: 'doctor', label: 'Doctor Share', route: '/accounting/doctor-commission' },
    { key: 'cash', label: 'Cash Closing', route: '/accounting/cash-closing' },
    { key: 'bank', label: 'Bank', route: '/accounting/bank' },
    { key: 'journals', label: 'Journals', route: '/accounting/journals' },
    { key: 'reports', label: 'Reports', route: '/accounting/reports' },
    { key: 'audit', label: 'Audit', route: '/accounting/audit' },
  ];

  loading = false;
  error = '';
  dashboard: AccountingDashboard | null = null;
  workspace: AccountingWorkspace | null = null;
  modal: '' | 'account' | 'journal' | 'advance' | 'refund' | 'discount' | 'insurance' | 'corporate' | 'supplier' | 'expense' = '';
  accountForm: Record<string, unknown> = { category: 'assets', normal_balance: 'debit', opening_balance: 0, current_balance: 0, is_active: true };
  workflowForm: Record<string, unknown> = { amount: 0, status: 'pending', payment_method: 'cash' };
  journalForm: Record<string, unknown> = {
    journal_date: this.today(),
    narration: '',
    source_module: 'manual',
    lines: [
      { account_code: '1001', account_name: 'Cash', debit_amount: 0, credit_amount: 0 },
      { account_code: '4000', account_name: 'Revenue', debit_amount: 0, credit_amount: 0 },
    ],
  };

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['accountingTab'] as AccountingTab) || 'dashboard');
      this.load();
    });
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.accountingService.dashboard().subscribe({
      next: (dashboard) => {
        this.dashboard = dashboard;
        this.loading = false;
      },
      error: () => {
        this.error = 'Accounting dashboard could not be loaded.';
        this.loading = false;
      },
    });
    this.accountingService.workspace().subscribe((workspace) => (this.workspace = workspace));
  }

  openTab(route: string): void {
    this.router.navigateByUrl(route);
  }

  openModal(modal: typeof this.modal): void {
    this.modal = modal;
    this.workflowForm = { amount: 0, status: modal === 'advance' ? 'active' : 'pending', payment_method: 'cash' };
  }

  closeModal(): void {
    this.modal = '';
  }

  saveAccount(): void {
    this.accountingService.createAccount(this.accountForm).subscribe(() => {
      this.notificationService.success('Account saved.');
      this.closeModal();
      this.load();
    });
  }

  saveJournal(): void {
    this.accountingService.createJournalEntry(this.journalForm).subscribe((entry) => {
      this.notificationService.success(`Journal ${entry.journal_number} posted.`);
      this.closeModal();
      this.load();
    });
  }

  saveWorkflow(kind: string): void {
    this.accountingService.createWorkflow(kind, this.workflowForm).subscribe(() => {
      this.notificationService.success('Finance record saved.');
      this.closeModal();
      this.load();
    });
  }

  recordsForTab(): FinanceRecord[] {
    if (!this.workspace) return [];
    if (this.tab() === 'collections') return this.workspace.advances;
    if (this.tab() === 'receivables') return [...this.workspace.insurance_claims, ...this.workspace.corporate_bills, ...this.workspace.discounts, ...this.workspace.refunds];
    if (this.tab() === 'payables') return this.workspace.supplier_invoices;
    if (this.tab() === 'expenses') return this.workspace.expenses;
    if (this.tab() === 'payroll') return [];
    if (this.tab() === 'doctor') return this.workspace.doctor_commissions;
    if (this.tab() === 'cash') return this.workspace.cash_closings;
    if (this.tab() === 'bank') return this.workspace.bank_transactions;
    return [];
  }

  num(value: string | number | null | undefined): number {
    return Number(value || 0);
  }

  money(value: string | number | null | undefined): string {
    return `BDT ${this.num(value).toLocaleString('en-BD', { maximumFractionDigits: 0 })}`;
  }

  max(points: ChartPoint[]): number {
    return Math.max(1, ...points.map((point) => this.num(point.value)));
  }

  statusClass(status: string): string {
    const value = (status || '').toLowerCase();
    if (['paid', 'approved', 'posted', 'matched', 'active'].includes(value)) return 'badge good';
    if (['pending', 'partial', 'open', 'payable', 'unmatched'].includes(value)) return 'badge warn';
    if (['rejected', 'cancelled', 'void'].includes(value)) return 'badge danger';
    return 'badge info';
  }

  today(): string {
    return new Date().toISOString().slice(0, 10);
  }
}
