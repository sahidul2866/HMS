import { AccountingOperationsComponent } from '../features/accounting/pages/accounting-journal/accounting-operations.component';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AccountingService } from '../features/accounting/services/accounting.service';
import { AccountingJournalComponent } from '../features/accounting/pages/accounting-journal/accounting-journal.component';
import { AccountingControlsComponent } from '../features/accounting/pages/accounting-journal/accounting-controls.component';
import { PatientService } from '../features/patients/services/patient.service';

describe('Accounting journal safeguards',()=>{
 let api:any;let component:AccountingJournalComponent;
 beforeEach(()=>{
  api=jasmine.createSpyObj('AccountingService',['dashboard','workspace','ledger','reports','createJournalEntry','controls']);
  api.dashboard.and.returnValue(of({kpis:[]}));api.workspace.and.returnValue(of({accounts:[],journal_entries:[]}));api.ledger.and.returnValue(of([]));api.reports.and.returnValue(of({}));api.createJournalEntry.and.returnValue(of({id:'journal',journal_number:'JE-TEST'}));api.controls.and.returnValue(of([]));
  TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting(),{provide:AccountingService,useValue:api},{provide:PatientService,useValue:{search:()=>of([])}},{provide:ActivatedRoute,useValue:{data:of({accountingTab:'dashboard'})}}]});
  component=TestBed.createComponent(AccountingJournalComponent).componentInstance;
 });
 it('starts a genuinely new journal instead of reusing the prior opening cash intent',()=>{
  component.openModal('journal');const first=component.journalForm['request_key'];
  component.journalForm['voucher_type']='opening';component.journalForm['status']='posted';component.journalForm['narration']='Original opening';(component.journalForm['lines'] as any[])[0].debit_amount=5000;
  component.closeModal();component.openModal('journal');
  expect(component.journalForm['request_key']).not.toBe(first);expect(component.journalForm['status']).toBe('draft');expect(component.journalForm['voucher_type']).toBe('journal');expect(component.journalForm['narration']).toBe('');expect((component.journalForm['lines'] as any[])[0].debit_amount).toBe(0);
 });
 it('keeps the same request identity for repeated submissions of one financial intent',()=>{
  component.openModal('journal');component.saveJournal();component.saveJournal();
  const first=api.createJournalEntry.calls.argsFor(0)[0];const second=api.createJournalEntry.calls.argsFor(1)[0];expect(first.request_key).toBe(second.request_key);
 });
 it('supports multi-account vouchers while retaining at least two lines',()=>{
  component.openModal('journal');component.addJournalLine();expect((component.journalForm['lines'] as any[]).length).toBe(3);component.removeJournalLine(2);component.removeJournalLine(0);expect((component.journalForm['lines'] as any[]).length).toBe(2);
 });
});

describe('Accounting statement printing',()=>{
 it('escapes report/entity text and prints ending balances and the accounting equation',()=>{
  TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});
  const component=TestBed.createComponent(AccountingControlsComponent).componentInstance;
  component.book={company:{legal_name:'<img onerror=bad>'},trial_balance:[{code:'1001',name:'Cash <script>bad</script>',debit:'50.00',credit:'0.00'}],total_debit:'50.00',total_credit:'50.00',profit_and_loss:{net_profit:'0.00'},balance_sheet:{assets:'50.00',liabilities:'0.00',equity:'50.00',unclosed_earnings:'0.00',equation_difference:'0.00'},cash_flow:{opening_balance:'0.00',net_change:'50.00',closing_balance:'50.00'}};
  const write=jasmine.createSpy('write');const print=jasmine.createSpy('print');spyOn(window,'open').and.returnValue({document:{write,close:()=>{}},focus:()=>{},print} as unknown as Window);
  component.printStatements();const html=write.calls.mostRecent().args[0];expect(html).toContain('&lt;img onerror=bad&gt;');expect(html).not.toContain('<script>bad</script>');expect(html).toContain('50.00');expect(html).toContain('Balance Sheet');expect(html).toContain('Cash Flow');expect(print).toHaveBeenCalled();
 });
});

describe('Accounting transfer request identity',()=>{
 it('reuses the transfer key on resubmission and changes it for a different amount',()=>{
  const api=jasmine.createSpyObj('AccountingService',['controlAction']);api.controlAction.and.returnValue(of({status:'draft'}));
  TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting(),{provide:AccountingService,useValue:api}]});
  const component=TestBed.createComponent(AccountingOperationsComponent).componentInstance;spyOn(component,'load');
  component.transfer={...component.transfer,from_account:'1001',to_account:'1020',amount:100,reference:'Verified deposit'};
  component.saveTransfer();component.saveTransfer();
  const first=api.controlAction.calls.argsFor(0)[1].request_key;expect(api.controlAction.calls.argsFor(1)[1].request_key).toBe(first);
  component.transfer.amount=200;component.saveTransfer();expect(api.controlAction.calls.argsFor(2)[1].request_key).not.toBe(first);
 });
});
