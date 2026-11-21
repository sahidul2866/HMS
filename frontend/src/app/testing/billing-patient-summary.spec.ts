import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Subject, of, throwError } from 'rxjs';
import { BillingPatientSummaryComponent } from '../features/billing/components/billing-patient-summary.component';
import { PatientService } from '../features/patients/services/patient.service';

describe('Billing patient summary',()=>{
 let api:any;let component:BillingPatientSummaryComponent;let fixture:any;
 const history=(id:string)=>({patient:{id,first_name:'Test',last_name:'Patient'},billing_invoices:[
  {id:'due',invoice_number:'INV-DUE',status:'posted',payment_status:'partial',total_amount:'100.25',paid_amount:'20.10',due_amount:'80.15'},
  {id:'paid',invoice_number:'INV-PAID',status:'posted',payment_status:'paid',total_amount:'50.10',paid_amount:'50.10',due_amount:'0'},
  {id:'void',invoice_number:'INV-VOID',status:'void',payment_status:'unpaid',total_amount:'999',paid_amount:'0',due_amount:'999'}
 ],billing_payments:[],opd_visits:[],appointments:[],ipd_admissions:[],pharmacy_dispenses:[]});
 beforeEach(()=>{api=jasmine.createSpyObj('PatientService',['getHistory']);api.getHistory.and.returnValue(of(history('one')));TestBed.configureTestingModule({providers:[provideRouter([]),{provide:PatientService,useValue:api}]});fixture=TestBed.createComponent(BillingPatientSummaryComponent);component=fixture.componentInstance;fixture.componentRef.setInput('patient',{id:'one',first_name:'Test',last_name:'Patient'});});
 it('shows exact credit dues and history without including void bills in totals',()=>{fixture.detectChanges();expect(component.totalDue).toBe(80.15);expect(component.totalBilled).toBe(150.35);expect(component.totalPaid).toBe(70.20);expect(component.dueInvoices.length).toBe(1);expect(api.getHistory).toHaveBeenCalledWith('one',true);const text=fixture.nativeElement.textContent;expect(text).toContain('INV-DUE');expect(text).toContain('INV-VOID');expect(text).toContain('Outstanding credit dues');expect(fixture.nativeElement.querySelector('a').getAttribute('href')).toContain('invoiceId=due');});
 it('opens new billing only when the user presses the button',()=>{const emit=spyOn(component.newBilling,'emit');fixture.detectChanges();expect(emit).not.toHaveBeenCalled();fixture.nativeElement.querySelector('button').click();expect(emit).toHaveBeenCalledTimes(1);});
 it('clears old patient data and ignores late responses when another patient is selected',()=>{const first=new Subject<any>();const second=new Subject<any>();api.getHistory.and.returnValues(first,second);fixture.detectChanges();fixture.componentRef.setInput('patient',{id:'two'});fixture.detectChanges();expect(component.history).toBeNull();first.next(history('one'));expect(component.history).toBeNull();second.next(history('two'));expect(component.history?.patient.id).toBe('two');});
 it('shows a retry message rather than zero dues after a history load failure',()=>{api.getHistory.and.returnValue(throwError(()=>new Error('Unavailable')));fixture.detectChanges();expect(component.history).toBeNull();expect(fixture.nativeElement.textContent).toContain('Retry to verify outstanding dues');expect(fixture.nativeElement.textContent).not.toContain('No outstanding credit dues');});
});
