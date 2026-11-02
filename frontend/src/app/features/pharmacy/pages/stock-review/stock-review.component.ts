import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SessionService } from '../../../../core/services/session.service';
import { PharmacyService } from '../../services/pharmacy.service';

interface Review { id:string;kind:string;status:string;details:Record<string,any>;submitted_by_id:string;submitted_by:string;reviewed_by:string|null;review_note:string|null;created_at:string; }
interface Receipt { id:string;dispense_id:string;medicine_name:string;quantity:string;batch_no:string|null;received_at:string; }
interface Legacy { dispense_id:string;medicine_name:string;unallocated_quantity:string;sources:Array<{id:string;batch_no:string|null;returnable:string}>; }
interface Batch { id:string;item_name:string;batch_no:string;quantity:string;store:string; }
interface Workspace { reviews:Review[];pending_disposals:Receipt[];legacy_returns:Legacy[];batches:Batch[]; }
@Component({selector:'app-stock-review',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./stock-review.component.html',styleUrls:['./stock-review.component.scss']})
export class StockReviewComponent {
 readonly session=inject(SessionService);private readonly api=inject(PharmacyService);
 data:Workspace={reviews:[],pending_disposals:[],legacy_returns:[],batches:[]};
 panel='reviews';loading=true;busy=false;error='';success='';search='';status='submitted';notes:Record<string,string>={};
 batchId='';count:number|null=null;reason='';evidence='';
 selectedReceipt:Receipt|null=null;selectedLegacy:Legacy|null=null;sourceId='';quantity:number|null=null;disposition='held_for_disposal';method='';witness='';performedAt='';
 constructor(){this.refresh();}
 get canSubmit(){return this.session.hasPermission('pharmacy.stock.adjust');}
 get canDispose(){return this.session.hasPermission('pharmacy.return');}
 get canApprove(){return this.session.hasPermission('pharmacy.stock.approve');}
 get visibleReviews(){const q=this.search.trim().toLowerCase();return this.data.reviews.filter(r=>(!this.status||r.status===this.status)&&(!q||JSON.stringify([r.details,r.submitted_by,r.kind]).toLowerCase().includes(q)));}
 get visibleBatches(){const q=this.search.trim().toLowerCase();return this.data.batches.filter(b=>!q||`${b.item_name} ${b.batch_no} ${b.store}`.toLowerCase().includes(q));}
 refresh(){this.loading=true;this.error='';this.api.stockWorkspace<Workspace>().subscribe({next:r=>{this.data=r;this.loading=false;},error:()=>{this.loading=false;this.error='Could not load stock reviews. Check your connection and retry.';}});}
 switchPanel(panel:string){this.panel=panel;this.search='';this.reason='';this.evidence='';this.error='';this.selectedReceipt=null;this.selectedLegacy=null;}
 chooseReceipt(r:Receipt){this.selectedReceipt=r;this.method='';this.witness='';this.reason='';this.evidence='';this.performedAt='';}
 chooseLegacy(r:Legacy){this.selectedLegacy=r;this.sourceId='';this.quantity=null;this.reason='';this.evidence='';}
 post(kind:string,body:object){if(this.busy)return;this.busy=true;this.error='';this.success='';this.api.submitStockReview<Review>(kind,body).subscribe({next:()=>{this.busy=false;this.success='Evidence submitted. A different supervisor must review it.';this.reason='';this.evidence='';this.selectedReceipt=null;this.selectedLegacy=null;this.batchId='';this.count=null;this.panel='reviews';this.refresh();},error:()=>{this.busy=false;this.error='Submission was not completed. Check the displayed validation message and retry.';}});}
 submitCount(){if(!this.batchId||this.count===null||this.count<0||this.reason.trim().length<5||this.evidence.trim().length<3)return;this.post('count',{batch_id:this.batchId,counted_quantity:this.count,reason:this.reason,evidence_reference:this.evidence});}
 submitLegacy(){if(!this.selectedLegacy||!this.sourceId||!this.quantity)return;this.post('legacy-return',{dispense_id:this.selectedLegacy.dispense_id,source_issue_id:this.sourceId,quantity:this.quantity,disposition:this.disposition,reason:this.reason,evidence_reference:this.evidence});}
 submitDisposal(){if(!this.selectedReceipt||!this.performedAt)return;this.post('disposal',{dispense_id:this.selectedReceipt.dispense_id,receipt_id:this.selectedReceipt.id,method:this.method,witness:this.witness,performed_at:new Date(this.performedAt).toISOString(),reason:this.reason,evidence_reference:this.evidence});}
 decide(r:Review,decision:string){if(this.busy||!this.notes[r.id]||this.notes[r.id].trim().length<5)return;this.busy=true;this.error='';this.api.decideStockReview<Review>(r.id,{decision,note:this.notes[r.id]}).subscribe({next:()=>{this.busy=false;this.success=decision==='approve'?'Review approved and recorded.':'Review rejected. Submit fresh evidence if needed.';this.refresh();},error:()=>{this.busy=false;this.error='Review was not completed. If stock changed, reject this record and perform a fresh count.';}});}
 ownReview(r:Review){return r.submitted_by_id===this.session.snapshot.user?.id;}
}
