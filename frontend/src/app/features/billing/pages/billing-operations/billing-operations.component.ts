import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { BillingServiceApi } from '../../services/billing.service';
import { BillingService, BillingType } from '../../models/billing.models';
import { SessionService } from '../../../../core/services/session.service';
import { NotificationService } from '../../../../core/services/notification.service';

interface Handover {id:string;number:string;collector_id:string;receiver_id:string;expected_amount:string;declared_amount:string;variance:string;status:string;created_at:string;note:string;acceptance_note?:string;}
interface Stats {snapshot_id:string;generated_at:string;totals:Record<string,string|number>;departments:Record<string,Record<string,string>>;payment_methods:Record<string,string>;creators:Record<string,Record<string,string>>;}
@Component({selector:'app-billing-operations',standalone:true,imports:[CommonModule,FormsModule,RouterLink],templateUrl:'./billing-operations.component.html',styles:[`
:host{display:block}.operations-tabs{display:flex;flex-wrap:wrap;gap:.5rem}.operations-content{min-width:0}.operations-content .page-card{max-width:1040px;margin-inline:auto} .table{display:table;min-width:640px}td:not(:first-child),th{white-space:nowrap}td:first-child{overflow-wrap:anywhere} form.form-grid{grid-template-columns:repeat(2,minmax(0,1fr)) auto;align-items:end}@media(max-width:640px){form.form-grid{grid-template-columns:minmax(0,1fr)}}.operations-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.7rem}.stat{padding:.8rem;border:1px solid var(--border);border-radius:10px;display:grid;gap:.3rem}.stat span{text-transform:capitalize;color:var(--text-muted)}.table-wrap{overflow:auto;max-width:100%}form{display:grid;gap:.8rem}input,select,textarea{width:100%;min-width:0}.panel-head{display:flex;gap:1rem;justify-content:space-between;flex-wrap:wrap}details>summary{cursor:pointer;font-weight:650;padding:.8rem 0}td,th{white-space:normal;min-width:90px}.history{display:grid;gap:.8rem}.history article{padding:.8rem;border:1px solid var(--border);border-radius:8px}.variance{color:var(--danger,#b91c1c)}@media(max-width:850px){.operations-grid{grid-template-columns:1fr}}
`]})
export class BillingOperationsComponent {
 readonly api=inject(BillingServiceApi);readonly session=inject(SessionService);private readonly notice=inject(NotificationService);
 receivers:{id:string;name:string}[]=[];
 types:BillingType[]=[];services:BillingService[]=[];handovers:Handover[]=[];stats:Stats|null=null;
 balance:{receipts:string;refunds:string;expected_amount:string;receipt_count:number;refund_count:number}|null=null;
 savedReports:{id:string;created_at:string;statistics:Stats;filters:Record<string,string>}[]=[];
 loading=true;busy=false;error='';dateFrom='';dateTo='';receiverId='';declaredAmount=0;handoverNote='';acceptNotes:Record<string,string>={};
 code='';name='';department='';serviceId='';typeId='';
 get admin(){return this.session.hasPermission('billing.service.manage');}
 activePanel: 'reports' | 'cash' | 'setup' = this.session.hasPermission('reporting.financial.view') ? 'reports' : this.session.hasPermission('billing.payment.collect') ? 'cash' : 'setup';
 constructor(){this.refresh();}
 refresh(){if(this.session.hasPermission('reporting.financial.view'))this.api.operations<typeof this.savedReports>('reports/snapshots').subscribe(r=>this.savedReports=r);this.error='';this.loading=true;this.api.listTypes().subscribe({next:t=>{this.types=t;this.loading=false;},error:e=>{this.error=e.message||'Could not load billing operations. Check your connection and retry.';this.loading=false;}});
  this.api.listServices().subscribe(s=>this.services=s);
  if(this.session.hasPermission('billing.payment.collect')){this.api.operations<{id:string;name:string}[]>('cash/receivers').subscribe(r=>this.receivers=r);this.api.operations<typeof this.balance>('cash/balance').subscribe(b=>this.balance=b);this.api.operations<Handover[]>('cash/handovers').subscribe(h=>this.handovers=h);}
 }
 report(){if(this.dateFrom&&this.dateTo&&this.dateFrom>this.dateTo){this.notice.warning('Choose an end date after the start date.');return;}this.busy=true;const query=new URLSearchParams();if(this.dateFrom)query.set('date_from',this.dateFrom);if(this.dateTo)query.set('date_to',this.dateTo);this.api.operations<Stats>('reports/operations?'+query).subscribe({next:s=>{this.stats=s;this.busy=false;this.api.operations<typeof this.savedReports>('reports/snapshots').subscribe(r=>this.savedReports=r);},error:()=>this.busy=false});}
 openSaved(id:string){const saved=this.savedReports.find(s=>s.id===id);if(saved)this.stats={...saved.statistics,snapshot_id:saved.id,generated_at:saved.created_at};}
 createType(){this.busy=true;this.api.createType({code:this.code,name:this.name,department:this.department}).subscribe({next:()=>{this.busy=false;this.code='';this.name='';this.department='';this.notice.success('Billing type saved. Link it to catalog items below.');this.refresh();},error:()=>this.busy=false});}
 linkItem(){const item=this.services.find(s=>s.id===this.serviceId);if(!item)return;this.busy=true;this.api.updateServiceControls(item.id,{billing_type_id:this.typeId||null,doctor_share_percentage:Number(item.doctor_share_percentage),max_discount_percentage:item.max_discount_percentage==null?null:Number(item.max_discount_percentage),max_discount_amount:item.max_discount_amount==null?null:Number(item.max_discount_amount),room_number:item.room_number,is_active:item.is_active}).subscribe({next:()=>{this.busy=false;this.notice.success('Item department mapping saved. New invoices retain this classification.');this.refresh();},error:()=>this.busy=false});}
 submitHandover(){this.busy=true;this.api.postOperation<Handover>('cash/handovers',{receiver_id:this.receiverId,declared_amount:this.declaredAmount,note:this.handoverNote}).subscribe({next:()=>{this.busy=false;this.notice.success('Cash handover submitted. The designated receiver must acknowledge it.');this.handoverNote='';this.refresh();},error:()=>this.busy=false});}
 accept(h:Handover){this.busy=true;this.api.postOperation<Handover>('cash/handovers/'+h.id+'/accept',{note:this.acceptNotes[h.id]}).subscribe({next:()=>{this.busy=false;this.notice.success('Cash handover accepted and recorded.');this.refresh();},error:()=>this.busy=false});}
 actorId(){return this.session.snapshot.user?.id;}
}
