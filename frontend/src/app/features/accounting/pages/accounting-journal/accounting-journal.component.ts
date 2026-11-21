import { AccountingControlsComponent } from './accounting-controls.component';
import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { SessionService } from '../../../../core/services/session.service';
import { PatientService } from '../../../patients/services/patient.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AccountingDashboard, AccountingReportSummary, AccountingWorkspace, ChartPoint, FinanceRecord, GeneralLedgerLine, JournalEntry } from '../../models/accounting.models';
import { AccountingService } from '../../services/accounting.service';

type AccountingTab = 'dashboard' | 'accounts' | 'ledger' | 'vouchers' | 'collections' | 'receivables' | 'payables' | 'expenses' | 'payroll' | 'doctor' | 'cash' | 'bank' | 'reports' | 'audit';

@Component({
  selector: 'app-accounting-journal',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, AccountingControlsComponent],
  templateUrl: './accounting-journal.component.html',
  styleUrls: ['./accounting-journal.component.scss'],
})
export class AccountingJournalComponent {
  readonly session=inject(SessionService);private readonly patientService=inject(PatientService);
  auditRows:any[]=[];patientMatches:any[]=[];patientQuery='';editingAccountId='';
  private readonly accountingService = inject(AccountingService);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  readonly tab = signal<AccountingTab>('dashboard');

  loading = false;
  error = '';
  dashboard: AccountingDashboard | null = null;
  workspace: AccountingWorkspace | null = null;
  ledger: GeneralLedgerLine[] = [];
  reports: AccountingReportSummary | null = null;
  modal: '' | 'account' | 'journal' | 'advance' | 'refund' | 'discount' | 'insurance' | 'corporate' | 'supplier' | 'expense' = '';
  accountForm: Record<string, unknown> = { category: 'assets', normal_balance: 'debit', opening_balance: 0, current_balance: 0, is_active: true };
  workflowForm: Record<string, unknown> = { amount: 0, status: 'pending', payment_method: 'cash' };
  journalForm: Record<string, unknown> = {
    journal_date: this.today(),
    narration: '',
    source_module: 'manual',
    status: 'draft',
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
    this.accountingService.ledger().subscribe((ledger) => (this.ledger = ledger));
    if(this.tab()==='audit')this.accountingService.controls<any[]>('audit').subscribe(rows=>this.auditRows=rows);
    this.accountingService.reports().subscribe((reports) => (this.reports = reports));
  }

  openModal(modal: typeof this.modal): void {
    this.modal = modal;
    if(modal==='account'){this.editingAccountId='';this.accountForm={category:'assets',normal_balance:'debit',opening_balance:0,current_balance:0,is_active:true,is_control:false};}
    if(modal==='journal')this.journalForm={journal_date:this.today(),narration:'',source_module:'manual',status:'draft',voucher_type:'journal',request_key:crypto.randomUUID(),lines:[{account_code:'1001',account_name:'Cash',debit_amount:0,credit_amount:0},{account_code:'4000',account_name:'Revenue',debit_amount:0,credit_amount:0}]};
    this.workflowForm = { amount: 0, status: 'pending', payment_method: 'cash',expense_account_code:'5180',purchase_account_code:'1300' };
  }

  closeModal(): void {
    this.modal = '';
  }

  saveAccount(): void {
    const request=this.editingAccountId?this.accountingService.updateAccount(this.editingAccountId,{name:this.accountForm['name'],parent_id:this.accountForm['parent_id']||null,reporting_group:this.accountForm['reporting_group']||null,is_active:this.accountForm['is_active']}):this.accountingService.createAccount(this.accountForm);
    request.subscribe(() => {
      this.notificationService.success('Account saved.');
      this.closeModal();
      this.load();
    });
  }

  editAccount(account:any):void{this.modal='account';this.editingAccountId=account.id;this.accountForm={...account};}
  searchAdvancePatient():void{this.patientService.search(this.patientQuery).subscribe(rows=>this.patientMatches=rows);}
  paySupplier(record:FinanceRecord):void{const amount=window.prompt('Actual supplier payment (BDT)',String(record.due_amount));if(!amount)return;const reference=window.prompt('Verified payment / bank reference');if(!reference||reference.trim().length<3)return;this.accountingService.controlAction('supplier-invoices/'+record.id+'/payments',{amount,reference,payment_method:'bank_transfer',request_key:crypto.randomUUID()}).subscribe(()=>this.load());}
  addJournalLine():void{(this.journalForm['lines'] as any[]).push({account_code:'',account_name:'',debit_amount:0,credit_amount:0,cost_center:''});}
  removeJournalLine(index:number):void{const lines=this.journalForm['lines'] as any[];if(lines.length>2)lines.splice(index,1);}
  saveJournal(): void {
    this.accountingService.createJournalEntry(this.journalForm).subscribe((entry) => {
      this.notificationService.success(`Voucher ${entry.journal_number} saved.`);
      this.closeModal();
      this.load();
    });
  }

  saveWorkflow(kind: string): void {
    this.accountingService.createWorkflow(kind, {...this.workflowForm,patient_id:this.workflowForm['patient_id']||null,receiving_id:this.workflowForm['receiving_id']||null,pharmacy_purchase_id:this.workflowForm['pharmacy_purchase_id']||null,due_date:this.workflowForm['due_date']||null,transaction_date:this.workflowForm['transaction_date']||null}).subscribe(() => {
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

  voucherAction(entry: JournalEntry, action: string): void {
    this.accountingService.voucherAction(entry.id, action).subscribe((result) => {
      this.notificationService.success(`${result.journal_number} is ${result.status}.`);
      this.load();
    });
  }

  approveRecord(record: FinanceRecord, kind: string): void {
    this.accountingService.updateFinanceStatus(kind, record.id, 'approved').subscribe(() => {
      this.notificationService.success('Record approved.');
      this.load();
    });
  }

  recordKind(): string {
    if (this.tab() === 'payables') return 'supplier';
    if (this.tab() === 'expenses') return 'expense';
    if (this.tab() === 'receivables') return 'insurance';
    return this.tab();
  }

  syncIntegrations(): void {
    this.accountingService.syncIntegrations().subscribe((result) => {
      this.notificationService.success(result.message);
      this.load();
    });
  }

  reportGroup(key: keyof AccountingReportSummary): ChartPoint[] {
    return this.reports?.[key] || [];
  }

  num(value: string | number | null | undefined): number {
    return Number(value || 0);
  }

  money(value: string | number | null | undefined): string {
    return `BDT ${this.num(value).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
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
