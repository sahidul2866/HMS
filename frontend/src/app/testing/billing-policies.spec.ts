import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { FinancialPoliciesComponent } from '../features/billing/pages/billing-settings/financial-policies.component';
import { BillingServiceApi } from '../features/billing/services/billing.service';
import { NotificationService } from '../core/services/notification.service';
import { BillingDeskComponent } from '../features/billing/pages/billing-desk/billing-desk.component';

describe('Financial policy administration', () => {
  let api: jasmine.SpyObj<BillingServiceApi>;
  let component: FinancialPoliciesComponent;
  beforeEach(() => {
    api = jasmine.createSpyObj('BillingServiceApi', ['operations', 'postOperation']);
    api.operations.and.returnValue(of([]));
    api.postOperation.and.returnValue(of({}));
    TestBed.configureTestingModule({providers: [
      {provide: BillingServiceApi, useValue: api},
      {provide: NotificationService, useValue: jasmine.createSpyObj('Notifications', ['success'])}
    ]});
    component = TestBed.createComponent(FinancialPoliciesComponent).componentInstance;
  });
  it('rejects invalid JSON before issuing a financial configuration request', () => {
    component.rulesText = '{invalid'; component.save();
    expect(api.postOperation).not.toHaveBeenCalled();
    expect(component.error).toBeTruthy();
  });
  it('saves effective dates and exact decimal strings as a new version', () => {
    component.effectiveFrom = '2026-11-19T10:00'; component.reason = 'Approved concession policy';
    component.rulesText = '{"discount_sharing":{"hospital":"70.25","doctor":"29.75"}}';
    component.save();
    const payload = api.postOperation.calls.mostRecent().args[1] as any;
    expect(payload.rules.discount_sharing.hospital).toBe('70.25');
    expect(payload.effective_from).toBe(new Date(component.effectiveFrom).toISOString());
    expect(component.busy).toBeFalse();
  });
  it('preserves the settlement request key and decimal amount after an error', () => {
    component.participant = 'doctor'; component.amount = '123.45'; component.settlementReason = 'Monthly earnings';
    api.postOperation.and.returnValue(throwError(() => Error('Network interrupted')));
    component.settle(); const first = api.postOperation.calls.mostRecent().args[1] as any;
    component.settle(); const retry = api.postOperation.calls.mostRecent().args[1] as any;
    expect(first.request_key).toBe(retry.request_key);
    expect(retry.amount).toBe('123.45');
  });
  it('keeps a copied historical policy intact while editing its new version', () => {
    const original = {id: 'policy', scope: 'item', selector: 'service', effective_from: '2026-11-19', reason: 'Original', rules: {max_percentage: '20'}};
    component.copy(original); component.rulesText = '{}';
    expect(original.rules.max_percentage).toBe('20');
    expect(component.reason).toBe('');
  });
});

describe('Invoice financial printing', () => {
  function print(visible: boolean): string {
    const desk = Object.create(BillingDeskComponent.prototype) as any;
    return desk.buildInvoicePrintHtml({invoice_number: 'INV-TEST', patient: {first_name: 'Test', last_name: 'Patient'},
      sub_total: '900.00', item_discount_amount: '100.00', invoice_discount_amount: '0.00', total_amount: '900.00', net_payable_amount: '450.00', paid_amount: '450.00', due_amount: '0.00', refunded_amount: '450.00', payments: [],
      items: [{service_name: 'Investigation', quantity: '2', unit_price: '500.00', discount_percentage: '10.00', line_total: '900.00', financial_snapshot: {rules: {show_item_discounts: visible, hospital_name: 'Test Hospital <HQ>'}}}]});
  }
  it('shows item discounts when configured and prints the current payable and refunds', () => {
    const html = print(true);
    expect(html).toContain('<td>10.00</td>');
    expect(html).toContain('Net payable after credits');
    expect(html).toContain('Refunded');
    expect(html).toContain('Investigation × 2');
    expect(html).toContain('Test Hospital &lt;HQ&gt;');
  });
  it('hides item percentages while retaining the total discount and actual net amount', () => {
    const html = print(false);
    expect(html).not.toContain('<td>10.00</td>');
    expect(html).toContain('Item Discount');
    expect(html).toContain('<td>—</td>');
  });
});
