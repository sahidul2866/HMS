import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BillingServiceApi } from '../../services/billing.service';
import { NotificationService } from '../../../../core/services/notification.service';

interface Policy { id: string; scope: string; selector: string; effective_from: string; reason: string; rules: Record<string, unknown>; }
interface Allocation { id: string; participant_key: string; component: string; amount: string; state: string; reason: string; }
@Component({
  selector: 'app-financial-policies', standalone: true, imports: [CommonModule, FormsModule],
  template: `
  <section class="page-card">
    <h2>Financial policies and settlements</h2>
    <p>Each save creates a new version. Finalized invoices retain their rules. Precedence: item, referrer, doctor, category, department, hospital. Branch overrides hospital rules at the same scope.</p>
    <div class="toolbar-row">
      <label>Scope <select [(ngModel)]="scope"><option *ngFor="let s of scopes" [value]="s">{{s}}</option></select></label>
      <label>Selector <input [(ngModel)]="selector" aria-label="Policy selector"></label>
      <label>Effective from <input type="datetime-local" [(ngModel)]="effectiveFrom"></label>
      <label>Effective until <input type="datetime-local" [(ngModel)]="effectiveUntil"></label>
    </div>
    <p>Use * for hospital; department name for department; billing type ID for category; service ID for item; user ID for doctor; referral ID for referrer. Participant account keys must identify the actual recipient.</p>
    <label>Financial rules (JSON, amounts as decimal strings)
      <textarea style="width:100%;min-height:340px;font-family:monospace" [(ngModel)]="rulesText" aria-label="Financial rules"></textarea>
    </label>
    <label>Reason <input [(ngModel)]="reason" aria-label="Policy reason"></label>
    <button class="primary-btn" (click)="save()" [disabled]="busy">Save new policy version</button>
    <p role="alert" *ngIf="error">{{error}}</p>
    <table><thead><tr><th>Scope</th><th>Selector</th><th>Effective</th><th>Reason</th><th></th></tr></thead>
      <tbody><tr *ngFor="let p of policies"><td>{{p.scope}}</td><td>{{p.selector}}</td><td>{{p.effective_from | date:'medium'}}</td><td>{{p.reason}}</td><td><button (click)="copy(p)">Create next version</button></td></tr></tbody></table>
    <h3>External referral sources</h3>
    <label>Code <input [(ngModel)]="referrerCode"></label>
    <label>Name <input [(ngModel)]="referrerName"></label>
    <label>Type <select [(ngModel)]="referrerType"><option *ngFor="let kind of referrerTypes" [value]="kind">{{kind}}</option></select></label>
    <button (click)="registerReferrer()" [disabled]="busy">Register referral source</button>
    <p *ngFor="let r of referrers">{{r.full_name}} ({{r.referrer_type}}) — {{r.id}}</p>
    <h3>Participant ledger</h3>
    <button (click)="loadLedger()">Refresh ledger</button>
    <p>Negative balances after reversals are recoverable from the participant. Pending commissions require approval before settlement.</p>
    <p *ngFor="let balance of balances">{{balance.key}} — net balance BDT {{balance.amount}} (includes pending earnings and recovery adjustments)</p>
    <table><thead><tr><th>Account</th><th>Component</th><th>BDT</th><th>State</th><th>Reason</th></tr></thead><tbody>
      <tr *ngFor="let r of ledger"><td>{{r.participant_key}}</td><td>{{r.component}}</td><td>{{r.amount}}</td><td>{{r.state}}</td><td>{{r.reason}}</td></tr>
    </tbody></table>
    <label>Participant account <input [(ngModel)]="participant"></label>
    <label>Settlement BDT <input [(ngModel)]="amount" inputmode="decimal"></label>
    <label>Settlement reason <input [(ngModel)]="settlementReason"></label>
    <label><input type="checkbox" [(ngModel)]="approvePending">Approve pending earnings</label>
    <button (click)="settle()" [disabled]="busy">Record settlement</button>
  </section>`
})
export class FinancialPoliciesComponent {
  private api = inject(BillingServiceApi);
  private notices = inject(NotificationService);
  scopes = ['hospital', 'department', 'category', 'doctor', 'referrer', 'item'];
  scope = 'hospital'; selector = '*'; effectiveFrom = ''; effectiveUntil = ''; reason = ''; error = ''; busy = false;
  participant = ''; amount = ''; settlementReason = ''; approvePending = false;
  settlementKey = crypto.randomUUID();
  policies: Policy[] = []; ledger: Allocation[] = [];
  get balances(): {key: string; amount: string}[] {
    const accounts = new Map<string, bigint>();
    for (const row of this.ledger) {
      const value = String(row.amount); const negative = value.startsWith('-');
      const [whole, fraction = ''] = value.replace('-', '').split('.');
      const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2));
      accounts.set(row.participant_key, (accounts.get(row.participant_key) ?? 0n) + (negative ? -cents : cents));
    }
    return Array.from(accounts, ([key, cents]) => { const abs = cents < 0n ? -cents : cents; return {key, amount: (cents < 0n ? '-' : '') + (abs / 100n).toString() + '.' + (abs % 100n).toString().padStart(2, '0')}; });
  }
  rulesText = JSON.stringify({default_discount_percentage: '0', override_roles: [], hospital_name: null, hospital_address: null, hospital_contact: null, allow_started_cancellation: false, package_cancellation: 'quantity', allow_advance_payments: false, discounts_allowed: true, max_percentage: '100', max_amount: null, combine: true, approval_required: false, allowed_roles: [], discount_sharing: {hospital: '100'}, doctor_key: null, doctor_revenue_percentage: '0', hospital_fixed_deduction: null, commission_enabled: false, commission_basis: 'net', commission_percentage: '0', commission_fixed: null, commission_limit: null, commission_approval_required: false, participants: [], refund_approval_required: false, consultation_cancellable: true, show_item_discounts: true}, null, 2);
  referrerCode = ''; referrerName = ''; referrerType = 'external_doctor';
  referrerTypes = ['external_doctor', 'pharmacy', 'person', 'agent', 'organization', 'other'];
  referrers: {id: string; full_name: string; referrer_type: string}[] = [];
  constructor() { this.load(); this.loadReferrers(); }
  loadReferrers(): void { this.api.operations<typeof this.referrers>('referrers').subscribe(rows => this.referrers = rows); }
  registerReferrer(): void {
    this.busy = true;
    this.api.postOperation('referrers', {doctor_code: this.referrerCode, full_name: this.referrerName, referrer_type: this.referrerType}).subscribe({next: () => { this.busy = false; this.referrerName = ''; this.referrerCode = ''; this.loadReferrers(); }, error: () => { this.busy = false; this.error = 'Referral source rejected. Check the name and unique code.'; }});
  }
  load(): void { this.api.operations<Policy[]>('policies').subscribe({next: p => this.policies = p}); }
  loadLedger(): void { this.api.operations<Allocation[]>('allocations').subscribe({next: r => this.ledger = r}); }
  copy(p: Policy): void { this.scope = p.scope; this.selector = p.selector; this.rulesText = JSON.stringify(p.rules, null, 2); this.reason = ''; }
  save(): void {
    let rules: unknown;
    try { rules = JSON.parse(this.rulesText); if (!this.effectiveFrom || this.reason.trim().length < 3) throw Error('Enter an effective date and reason.'); }
    catch (e) { this.error = e instanceof Error ? e.message : 'Invalid rules'; return; }
    this.busy = true; this.error = '';
    this.api.postOperation('policies', {scope: this.scope, selector: this.selector, effective_from: new Date(this.effectiveFrom).toISOString(), effective_until: this.effectiveUntil ? new Date(this.effectiveUntil).toISOString() : null, reason: this.reason, rules}).subscribe({
      next: () => { this.busy = false; this.notices.success('Policy version saved'); this.load(); },
      error: () => { this.busy = false; this.error = 'Policy rejected. Check shares, participants, permissions and effective dates.'; }
    });
  }
  settle(): void {
    if (!this.participant || !/^\d+(\.\d{1,2})?$/.test(this.amount) || this.settlementReason.trim().length < 3) { this.error = 'Enter an account, valid BDT amount and settlement reason.'; return; }
    this.busy = true;
    this.api.postOperation('settlements', {participant_key: this.participant, amount: this.amount, request_key: this.settlementKey, reason: this.settlementReason, approve_pending: this.approvePending}).subscribe({
      next: () => { this.busy = false; this.settlementKey = crypto.randomUUID(); this.amount = ''; this.loadLedger(); this.notices.success('Settlement recorded'); },
      error: () => { this.busy = false; this.error = 'Settlement rejected. Check approved balance and permissions.'; }
    });
  }
}
