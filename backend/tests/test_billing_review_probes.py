"""Independent review probes for billing edge cases (returns, rounding, IPD consolidation)."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from test_opd_workflow_integration import database, db, seed  # noqa: F401
from app.core.exceptions import AppException
from app.modules.billing.service import BillingServiceManager
from app.modules.billing.operations import BillingOperations
from app.modules.ipd.service import IPDService
from app.schemas.billing import (BillingTypeCreate, BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate,
    BillingRefundCreate, BillingReturnCreate, BillingReturnItemCreate, BillingServiceCreate)
from app.schemas.encounter import IPDAdmissionCreate


def make(db, price, name='Review service'):
    actor, doctors, patient, _ = seed(db)
    service = BillingServiceManager(db)
    config = service.create_service(BillingServiceCreate(service_code='REV-' + name[:3].upper(), name=name, unit_price=price, doctor_share_percentage=0, max_discount_percentage=50), actor, {})
    return actor, doctors, patient, service, config


def test_fully_returned_invoice_is_not_reported_as_paid(db):
    actor, _, patient, service, config = make(db, 100)
    invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, items=[BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=1)]), actor, {})
    invoice = service.create_payment(invoice.id, BillingPaymentCreate(amount=100, payment_method='cash'), actor, {})
    invoice = service.create_return(invoice.id, BillingReturnCreate(reason='Whole service returned', items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id, quantity=1)]), actor, {})
    assert invoice.paid_amount == 0 and invoice.due_amount == 0
    assert invoice.payment_status != 'paid', 'a fully returned, fully refunded invoice must not read as paid'


def test_every_line_of_a_discounted_invoice_can_be_returned(db):
    actor, _, patient, service, config = make(db, Decimal('3.33'))
    invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, discount_percentage=10, discount_reason='Synthetic approved concession',
        items=[BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=1) for _ in range(3)]), actor, {})
    invoice = service.create_payment(invoice.id, BillingPaymentCreate(amount=invoice.total_amount, payment_method='cash'), actor, {})
    returned = Decimal(0)
    for item in invoice.items:
        invoice = service.create_return(invoice.id, BillingReturnCreate(reason='Return every line', items=[BillingReturnItemCreate(invoice_item_id=item.id, quantity=1)]), actor, {})
    returned = sum((r.credit_amount for r in invoice.refunds if r.refund_type == 'return'), Decimal(0))
    assert returned == invoice.refunded_amount
    assert invoice.paid_amount == 0 and returned <= invoice.total_amount


def test_return_on_partially_paid_invoice_credits_the_balance(db):
    actor, _, patient, service, config = make(db, 100)
    invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, items=[BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=2)]), actor, {})
    invoice = service.create_payment(invoice.id, BillingPaymentCreate(amount=20, payment_method='cash'), actor, {})
    # One unit (100) is returned although only 20 was collected: it should cancel debt, not need a cash payout.
    invoice = service.create_return(invoice.id, BillingReturnCreate(reason='Unused unit cancelled', items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id, quantity=1)]), actor, {})
    assert invoice.due_amount == 80


def interim_final(db, price=100):
    actor, doctors, patient, service, config = make(db, price)
    admission = IPDService(db).create_admission(IPDAdmissionCreate(patient_id=patient.id, admitted_at=datetime.now(UTC), admission_type='General', ward_name='Ward A', bed_number='B-1', attending_doctor_name=doctors[0].full_name), actor, {})
    def create_interim(qty, discount=0):
        return service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, source_ipd_admission_id=admission.id, source_module='ipd', billing_stage='ipd_interim',
            discount_percentage=discount, discount_reason='Synthetic approved concession' if discount else None,
            items=[BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=qty)]), actor, {})
    def create_final(extra_qty=0):
        draft = service.build_ipd_admission_draft(admission.id, actor, stage='final')
        lines = [BillingInvoiceItemCreate(billing_service_id=i.billing_service_id, quantity=i.quantity, carry_forward_item_id=i.carry_forward_item_id, source_label=i.source_label, source_module=i.source_module)
                 for i in draft.items if i.carry_forward_item_id]
        if extra_qty:
            lines.append(BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=extra_qty))
        return service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, source_ipd_admission_id=admission.id, source_module='ipd', billing_stage='ipd_final', items=lines), actor, {})
    return actor, service, create_interim, create_final, config, admission, patient


def test_consolidation_does_not_count_refunded_interim_money_as_paid(db):
    actor, service, interim_for, final_for, *_ = interim_final(db)
    interim = interim_for(10)  # 1000
    interim = service.create_payment(interim.id, BillingPaymentCreate(amount=1000, payment_method='cash'), actor, {})
    service.create_refund(interim.id, BillingRefundCreate(amount=400, reason='Deposit partly returned'), actor, {})
    final = final_for()
    assert final.paid_amount == 600, f'only 600 remains collected, final shows {final.paid_amount}'
    assert final.due_amount == 400 and final.refunded_amount == 400
    assert final.paid_amount == sum((p.amount for p in final.payments), Decimal(0)) - sum((r.amount for r in final.refunds), Decimal(0))


def test_final_bill_keeps_interim_price_and_invoice_discount(db):
    from app.models.billing import BillingItemConfig
    actor, service, interim_for, final_for, config, *_ = interim_final(db)
    interim = interim_for(10, discount=10)  # 1000 less 10% = 900
    assert interim.total_amount == 900
    service.create_payment(interim.id, BillingPaymentCreate(amount=900, payment_method='cash'), actor, {})
    db.get(BillingItemConfig, config['id']).unit_price = Decimal('120')  # catalog price rises after the interim bill
    db.flush()
    final = final_for()
    assert final.total_amount == 900, f'interim price/discount were not preserved: {final.total_amount}'
    assert final.paid_amount == 900 and final.due_amount == 0
    assert 'Synthetic approved concession' in (final.discount_reason or '')
    line = final.items[0]
    assert line.unit_price == 100 and line.discount_amount == 100


def test_final_bill_must_carry_every_interim_line(db):
    actor, service, interim_for, _, config, admission, patient = interim_final(db)
    interim = interim_for(10)
    service.create_payment(interim.id, BillingPaymentCreate(amount=1000, payment_method='cash'), actor, {})
    with pytest.raises(AppException, match='carried forward'):
        service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, source_ipd_admission_id=admission.id, source_module='ipd', billing_stage='ipd_final',
            items=[BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=1)]), actor, {})


def test_final_bill_does_not_rebill_items_returned_on_interim(db):
    actor, service, interim_for, final_for, *_ = interim_final(db)
    interim = interim_for(10)
    interim = service.create_payment(interim.id, BillingPaymentCreate(amount=1000, payment_method='cash'), actor, {})
    interim = service.create_return(interim.id, BillingReturnCreate(reason='Four units returned', items=[BillingReturnItemCreate(invoice_item_id=interim.items[0].id, quantity=4)]), actor, {})
    final = final_for()
    assert sum(i.quantity for i in final.items) == 6 and final.total_amount == 600
    assert final.paid_amount == 600 and final.due_amount == 0


def test_random_payment_refund_return_sequences_keep_money_reconciled(db):
    """Property check: whatever succeeds must leave paid/due/returned/custody mutually consistent."""
    import random
    from app.modules.billing.operations import BillingOperations
    rng = random.Random(20261101)
    actor, _, patient, service, config = make(db, Decimal('7.77'))
    ops = BillingOperations(db)
    accepted = rejected = 0  # rejected actions must leave state untouched; the invariants below prove it
    for round_no in range(40):
        lines = [BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=Decimal(rng.randint(1, 4)), discount_percentage=Decimal(rng.choice([0, 0, 5, 12.5]))) for _ in range(rng.randint(1, 4))]
        pct = Decimal(rng.choice([0, 0, 10, 7.5]))
        invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, discount_percentage=pct, discount_reason='Synthetic approved concession' if pct or any(l.discount_percentage for l in lines) else None, items=lines), actor, {})
        for _ in range(rng.randint(2, 7)):
            action = rng.choice(['pay', 'pay', 'refund', 'return'])
            try:
                if action == 'pay' and invoice.due_amount > 0:
                    amount = (invoice.due_amount if rng.random() < .5 else Decimal(rng.randint(1, max(1, int(invoice.due_amount)))))
                    invoice = service.create_payment(invoice.id, BillingPaymentCreate(amount=min(amount, invoice.due_amount), payment_method=rng.choice(['cash', 'card'])), actor, {})
                elif action == 'refund':
                    invoice = service.create_refund(invoice.id, BillingRefundCreate(amount=Decimal(rng.randint(1, 20)), payment_method=rng.choice(['cash', 'card']), reason='Synthetic refund'), actor, {})
                elif action == 'return':
                    item = rng.choice(invoice.items)
                    invoice = service.create_return(invoice.id, BillingReturnCreate(reason='Synthetic return', payment_method=rng.choice(['cash', 'card']), items=[BillingReturnItemCreate(invoice_item_id=item.id, quantity=Decimal(rng.choice([1, 1, 2])))]), actor, {})
                else:
                    continue
                accepted += 1
            except AppException:
                rejected += 1
            returned = sum((r.credit_amount for r in invoice.refunds if r.refund_type == 'return'), Decimal(0))
            paid = sum((p.amount for p in invoice.payments), Decimal(0)) - sum((r.amount for r in invoice.refunds), Decimal(0))
            assert invoice.paid_amount == paid, (round_no, invoice.paid_amount, paid)
            assert invoice.refunded_amount == sum((r.amount for r in invoice.refunds), Decimal(0))
            assert invoice.due_amount == max(Decimal(0), invoice.total_amount - returned - invoice.paid_amount)
            assert returned <= invoice.total_amount, (round_no, returned, invoice.total_amount)
            assert invoice.paid_amount >= 0 and invoice.due_amount >= 0
            for payment in invoice.payments:
                assert sum((r.amount for r in payment.refunds), Decimal(0)) <= payment.amount
            assert invoice.total_amount == invoice.sub_total - invoice.invoice_discount_amount
    assert accepted > 50
    from sqlalchemy import select
    from app.models.billing import BillingPayment, BillingRefund
    cash_in = sum((p.amount for p in db.scalars(select(BillingPayment)) if p.payment_method == 'cash'), Decimal(0))
    cash_out = sum((r.amount for r in db.scalars(select(BillingRefund)) if r.payment_method == 'cash'), Decimal(0))
    assert ops.cash_balance(actor)['expected_amount'] == cash_in - cash_out


def test_other_branch_user_cannot_read_or_change_an_invoice(db):
    from app.models.branch import Branch
    from app.models.user import User
    actor, _, patient, service, config = make(db, 100)
    invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, items=[BillingInvoiceItemCreate(billing_service_id=config['id'], quantity=1)]), actor, {})
    other_branch = Branch(code='XB-' + str(invoice.id)[:6], name='Other review branch')
    db.add(other_branch); db.flush()
    outsider = User(branch_id=other_branch.id, username='outsider' + str(invoice.id)[:6], email=str(invoice.id)[:6] + '@outsider.test', full_name='Outsider', hashed_password='unused', direct_permissions=list(actor.direct_permissions))
    db.add(outsider); db.flush()
    attempts = [
        lambda: service.get_invoice(invoice.id, outsider),
        lambda: service.create_payment(invoice.id, BillingPaymentCreate(amount=10, payment_method='cash'), outsider, {}),
        lambda: service.create_refund(invoice.id, BillingRefundCreate(amount=1, reason='Cross-branch attempt'), outsider, {}),
        lambda: service.create_return(invoice.id, BillingReturnCreate(reason='Cross-branch attempt', items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id, quantity=1)]), outsider, {}),
        lambda: BillingOperations(db).amend(invoice.id, __import__('app.schemas.billing', fromlist=['BillingInvoiceAmend']).BillingInvoiceAmend(note='x', reason='Cross-branch attempt'), outsider),
        lambda: BillingOperations(db).history(invoice.id, outsider),
        lambda: service.void_invoice(invoice.id, __import__('app.schemas.billing', fromlist=['BillingInvoiceVoidRequest']).BillingInvoiceVoidRequest(reason='Cross-branch attempt'), outsider, {}),
    ]
    for attempt in attempts:
        with pytest.raises(AppException) as error:
            attempt()
        assert error.value.status_code in (403, 404)
