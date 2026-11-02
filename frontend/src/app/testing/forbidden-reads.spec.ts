import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { errorInterceptor } from '../core/interceptors/error.interceptor';
import { NotificationService } from '../core/services/notification.service';

describe('forbidden responses',()=>{
 let errors:string[];let http:HttpClient;let backend:HttpTestingController;
 beforeEach(()=>{
  errors=[];
  TestBed.configureTestingModule({providers:[provideHttpClient(withInterceptors([errorInterceptor])),provideHttpClientTesting(),{provide:NotificationService,useValue:{error:(m:string)=>errors.push(m)}}]});
  http=TestBed.inject(HttpClient);backend=TestBed.inject(HttpTestingController);
 });
 const fail=(method:string,url:string,message:string,code='forbidden')=>{
  http.request(method,url).subscribe({error:()=>{}});
  backend.expectOne(url).flush({error:{code,message}},{status:403,statusText:'Forbidden'});
 };
 it('does not warn when a page reads lookup data its role may not see',()=>{
  fail('GET','/api/v1/users/doctors','Missing permissions: billing.view');
  fail('GET','/api/v1/billing/reports/summary','Requires any of: reporting.financial.view');
  expect(errors).toEqual([]);
 });
 it('still tells the user when a change is refused',()=>{
  fail('POST','/api/v1/billing/invoices','Missing permissions: billing.invoice.create');
  expect(errors.length).toBe(1);
 });
 it('shows the server explanation for a scope restriction',()=>{
  fail('GET','/api/v1/opd/visits','Doctor-wise OPD access must be granted from administration');
  expect(errors).toEqual(['Doctor-wise OPD access must be granted from administration']);
 });
});
