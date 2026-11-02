import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { PharmacyMedicinesComponent } from '../features/pharmacy/pages/pharmacy-medicines/pharmacy-medicines.component';
import { PharmacyService } from '../features/pharmacy/services/pharmacy.service';
import { SessionService } from '../core/services/session.service';
import { ActionConfirmationService } from '../core/services/action-confirmation.service';
import { NotificationService } from '../core/services/notification.service';

function render(permissions: string[]) {
  const catalog = {items:[{id:'medicine',name:'Review medicine',stock_quantity:'10',sale_price:'12',reorder_level:'2'}],page:1,page_size:10,total:1};
  TestBed.configureTestingModule({imports:[PharmacyMedicinesComponent],providers:[provideRouter([]),
    {provide:SessionService,useValue:{hasPermission:(code:string)=>permissions.includes(code),hasAnyPermission:(codes:string[])=>codes.some(code=>permissions.includes(code))}},
    {provide:PharmacyService,useValue:{listMedicineTypes:()=>of({items:[]}),listGenerics:()=>of({items:[]}),listCompanies:()=>of({items:[]}),listMedicines:()=>of(catalog)}},
    {provide:ActionConfirmationService,useValue:{}},{provide:NotificationService,useValue:{}},
  ]});
  const fixture=TestBed.createComponent(PharmacyMedicinesComponent);fixture.detectChanges();return fixture;
}

describe('pharmacy catalog permissions',()=>{
 it('lets a viewer inspect stock without offering actions their account cannot perform',()=>{
  const fixture=render(['pharmacy.view']);
  expect(fixture.nativeElement.textContent).toContain('Review medicine');
  expect(fixture.nativeElement.querySelector('.medicine-editor')).toBeNull();
  expect(fixture.nativeElement.querySelector('.row-action-menu')).toBeNull();
 });
 it('keeps catalog creation collapsed for stock managers and limits sales/purchase actions',()=>{
  const fixture=render(['pharmacy.view','pharmacy.stock.adjust']);
  expect((fixture.nativeElement.querySelector('.medicine-editor') as HTMLDetailsElement).open).toBeFalse();
  const actions=Array.from(fixture.nativeElement.querySelectorAll('.row-action-menu button') as NodeListOf<HTMLButtonElement>).map(button=>button.textContent?.trim());
  expect(actions).toEqual(['Edit','Delete']);
 });
});
