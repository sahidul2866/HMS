import { CommonModule } from '@angular/common';
import { Component, Input, Output, EventEmitter, OnChanges, OnDestroy, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { Patient, PatientClinicalHistory } from '../../patients/models/patient.models';
import { PatientService } from '../../patients/services/patient.service';
import { PatientContextPanelComponent } from '../../../shared/components/patient-context-panel/patient-context-panel.component';

@Component({selector:'app-billing-patient-summary',standalone:true,imports:[CommonModule,RouterLink,PatientContextPanelComponent],template:`
<section class="summary-card" aria-label="Patient billing history">
  <div class="summary-heading"><div><h2>Patient history & credit dues</h2><p>Review previous bills before starting a new invoice.</p></div><button type="button" class="primary-btn" (click)="newBilling.emit()">New Billing</button></div>
  @if(loading){<p role="status">Loading patient billing history…</p>}
  @else if(error){<p role="alert">{{error}}</p><button type="button" class="secondary-btn" (click)="load()">Retry history</button>}
  @else if(history){
    <div class="totals"><article><span>Previous invoices</span><strong>{{invoices.length}}</strong></article><article><span>Total billed</span><strong>{{totalBilled | currency:'BDT':'symbol':'1.2-2'}}</strong></article><article><span>Paid against bills</span><strong>{{totalPaid | currency:'BDT':'symbol':'1.2-2'}}</strong></article><article class="due"><span>Outstanding credit dues</span><strong>{{totalDue | currency:'BDT':'symbol':'1.2-2'}}</strong><small>{{dueInvoices.length}} unpaid / partially paid bill(s)</small></article></div>
    <h3>Credit dues</h3>
    @if(!dueInvoices.length){<p>No outstanding credit dues.</p>}
    @else{<div class="table-scroll"><table><thead><tr><th>Invoice</th><th>Date</th><th>Bill total</th><th>Paid</th><th>Due</th><th>Action</th></tr></thead><tbody>@for(invoice of dueInvoices;track invoice.id){<tr><td>{{invoice.invoice_number}}</td><td>{{invoice.created_at | date:'mediumDate'}}</td><td>{{invoice.total_amount | currency:'BDT':'symbol':'1.2-2'}}</td><td>{{invoice.paid_amount | currency:'BDT':'symbol':'1.2-2'}}</td><td class="due">{{invoice.due_amount | currency:'BDT':'symbol':'1.2-2'}}</td><td><a [routerLink]="['/billing/list']" [queryParams]="{invoiceId:invoice.id}">View / collect dues</a></td></tr>}</tbody></table></div>}
    <h3>Billing history</h3>
    <div class="table-scroll"><table><thead><tr><th>Invoice</th><th>Date</th><th>Status</th><th>Total</th><th>Paid</th><th>Due</th></tr></thead><tbody>@for(invoice of history.billing_invoices;track invoice.id){<tr><td><a [routerLink]="['/billing/list']" [queryParams]="{invoiceId:invoice.id}">{{invoice.invoice_number}}</a></td><td>{{invoice.created_at | date:'mediumDate'}}</td><td>{{invoice.status}} · {{invoice.payment_status}}</td><td>{{invoice.total_amount | currency:'BDT':'symbol':'1.2-2'}}</td><td>{{invoice.paid_amount | currency:'BDT':'symbol':'1.2-2'}}</td><td>{{invoice.due_amount | currency:'BDT':'symbol':'1.2-2'}}</td></tr>}@empty{<tr><td colspan="6">No previous invoices for this patient.</td></tr>}</tbody></table></div>
    <details><summary>Payment receipts ({{history.billing_payments.length}})</summary><div class="table-scroll"><table><thead><tr><th>Receipt</th><th>Invoice</th><th>Date</th><th>Method</th><th>Amount</th></tr></thead><tbody>@for(payment of history.billing_payments;track payment.id){<tr><td>{{payment.receipt_number}}</td><td>{{payment.invoice_number}}</td><td>{{payment.received_at | date:'medium'}}</td><td>{{payment.payment_method}}</td><td>{{payment.amount | currency:'BDT':'symbol':'1.2-2'}}</td></tr>}@empty{<tr><td colspan="5">No payment receipts.</td></tr>}</tbody></table></div></details>
    <details><summary>Visits, admissions & clinical history</summary><app-patient-context-panel [patient]="patient" [history]="history" [compact]="true"></app-patient-context-panel></details>
  }
</section>
`,styles:[`.summary-card{padding:20px;border:1px solid #dce4ec;border-radius:12px;background:var(--surface,#fff)}.summary-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}h2{margin:0}p{color:#526177}.totals{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}.totals article{display:flex;flex-direction:column;gap:8px;padding:16px;background:#f4f7fb;border-radius:8px}.totals strong{font-size:1.25rem}.due{color:#a43120}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left}th,td{padding:12px;border-bottom:1px solid #e0e6ec;white-space:nowrap}details{margin-top:20px}summary{cursor:pointer;font-weight:600}`]})
export class BillingPatientSummaryComponent implements OnChanges,OnDestroy {
 private readonly patients=inject(PatientService);private request?:Subscription;
 @Input({required:true}) patient!:Patient;@Output() newBilling=new EventEmitter<void>();
 history:PatientClinicalHistory|null=null;loading=false;error='';
 ngOnChanges():void{this.load();}ngOnDestroy():void{this.request?.unsubscribe();}
 get invoices(){return (this.history?.billing_invoices||[]).filter(row=>!['void','voided','cancelled','canceled','draft'].includes(row.status.toLowerCase()));}
 get dueInvoices(){return this.invoices.filter(row=>Number(row.due_amount)>0);}
 private sum(field:'total_amount'|'paid_amount'|'due_amount',rows=this.invoices):number{return rows.reduce((total,row)=>total+Math.round(Number(row[field]||0)*100),0)/100;}
 get totalBilled(){return this.sum('total_amount');}get totalPaid(){return this.sum('paid_amount');}get totalDue(){return this.sum('due_amount',this.dueInvoices);}
 load():void{this.request?.unsubscribe();this.history=null;this.error='';if(!this.patient?.id)return;this.loading=true;this.request=this.patients.getHistory(this.patient.id,true).subscribe({next:history=>{this.history=history;this.loading=false;},error:()=>{this.loading=false;this.error='Patient history could not be loaded. Retry to verify outstanding dues.';}});}
}
