"""Counter billing the way Bangladeshi hospitals run it: Taka discounts, part payments, mobile-banking proof, amount in words."""
from decimal import Decimal

import pytest
from sqlalchemy import select

from test_opd_workflow_integration import database, db, seed, visit  # noqa: F401
from app.core.exceptions import AppException
from app.models.billing import BillingItemConfig
from app.modules.billing.service import BillingServiceManager
from app.schemas.billing import BillingInvoiceAmend, BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate
from app.utils.bdt import amount_in_words


def bill(db, **extra):
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    billing = BillingServiceManager(db)
    billing.list_services(actor)
    config = db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module == "opd", BillingItemConfig.unit_price == 500))
    item_extra = extra.pop("item", {})
    payload = BillingInvoiceCreate(patient_id=patient.id, source_opd_visit_id=current.id, source_module="opd", billing_stage="opd",
                                   items=[BillingInvoiceItemCreate(billing_service_id=config.id, quantity=1, **item_extra)], **extra)
    return billing, actor, billing.create_invoice(payload, actor, {})


def test_item_discount_can_be_a_flat_taka_amount(db):
    _, _, invoice = bill(db, item={"discount_amount": Decimal("100")}, discount_reason="Management approval")
    assert invoice.items[0].discount_amount == Decimal("100.00") and invoice.items[0].discount_percentage == Decimal("20.00")
    assert invoice.items[0].line_total == Decimal("400.00") and invoice.total_amount == Decimal("400.00")


def test_whole_invoice_discount_can_be_a_flat_taka_amount(db):
    _, _, invoice = bill(db, discount_amount=Decimal("50"), discount_reason="Staff concession")
    assert invoice.invoice_discount_amount == Decimal("50.00") and invoice.discount_percentage == Decimal("10.00")
    assert invoice.total_amount == Decimal("450.00") and invoice.discount_amount == Decimal("50.00")


def test_item_and_invoice_discounts_stack(db):
    _, _, invoice = bill(db, item={"discount_amount": Decimal("100")}, discount_percentage=Decimal("10"), discount_reason="Approved by director")
    assert invoice.sub_total == Decimal("400.00") and invoice.invoice_discount_amount == Decimal("40.00")
    assert invoice.discount_amount == Decimal("140.00") and invoice.total_amount == Decimal("360.00")


def test_percentage_and_amount_together_are_refused(db):
    with pytest.raises(AppException) as error:
        bill(db, item={"discount_amount": Decimal("10"), "discount_percentage": Decimal("5")}, discount_reason="Both given")
    assert error.value.code == "billing_discount_ambiguous"


def test_discount_larger_than_the_bill_is_refused(db):
    with pytest.raises(AppException) as error:
        bill(db, discount_amount=Decimal("501"), discount_reason="Too much")
    assert error.value.code == "billing_discount_exceeds_amount"


def test_a_taka_discount_needs_a_reason_like_a_percentage(db):
    with pytest.raises(AppException) as error:
        bill(db, discount_amount=Decimal("20"))
    assert error.value.code == "billing_discount_reason_required"


def test_invoice_amend_accepts_a_flat_taka_discount(db):
    billing, actor, invoice = bill(db)
    amended = billing.amend_invoice(invoice.id, BillingInvoiceAmend(reason="Concession agreed at desk", discount_amount=Decimal("75")), actor) if hasattr(billing, "amend_invoice") else None
    if amended is None:
        from app.modules.billing.operations import BillingOperations
        amended = BillingOperations(db).amend(invoice.id, BillingInvoiceAmend(reason="Concession agreed at desk", discount_amount=Decimal("75")), actor)
    assert amended.invoice_discount_amount == Decimal("75.00") and amended.total_amount == Decimal("425.00")


def test_part_payments_then_the_rest_later(db):
    billing, actor, invoice = bill(db)
    invoice = billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("200"), payment_method="cash"), actor, {})
    assert invoice.payment_status == "partial" and invoice.due_amount == Decimal("300.00")
    invoice = billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("150"), payment_method="mobile_banking", payment_provider="bkash", reference_number="8n7a6d5ee7"), actor, {})
    assert invoice.payment_status == "partial" and invoice.due_amount == Decimal("150.00")
    with pytest.raises(AppException) as error:
        billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("151"), payment_method="cash"), actor, {})
    assert error.value.code == "billing_payment_exceeds_due"
    invoice = billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("150"), payment_method="card", reference_number="A12345"), actor, {})
    assert invoice.payment_status == "paid" and invoice.due_amount == Decimal("0.00")
    assert [(p.payment_method, p.payment_provider, p.reference_number) for p in sorted(invoice.payments, key=lambda p: p.created_at)] == [("cash", None, None), ("mobile_banking", "bkash", "8N7A6D5EE7"), ("card", None, "A12345")]
    assert invoice.payments[0].amount_in_words.endswith("Only") and invoice.total_in_words == "Taka Five Hundred Only"


@pytest.mark.parametrize("payload,code", [
    (dict(payment_method="mobile_banking", reference_number="8N7A6D5EE7"), "billing_payment_provider_required"),
    (dict(payment_method="mobile_banking", payment_provider="bkash"), "billing_payment_reference_required"),
    (dict(payment_method="mobile_banking", payment_provider="visa", reference_number="8N7A6D5EE7"), "billing_payment_provider_required"),
    (dict(payment_method="mobile_banking", payment_provider="nagad", reference_number="12"), "billing_payment_reference_invalid"),
    (dict(payment_method="card"), "billing_payment_reference_required"),
    (dict(payment_method="bank_transfer", reference_number="x y!"), "billing_payment_reference_invalid"),
])
def test_non_cash_receipts_need_proof(db, payload, code):
    billing, actor, invoice = bill(db)
    with pytest.raises(AppException) as error:
        billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("100"), **payload), actor, {})
    assert error.value.code == code


def test_a_transaction_id_cannot_settle_two_receipts(db):
    billing, actor, invoice = bill(db)
    proof = dict(payment_method="mobile_banking", payment_provider="nagad", reference_number="TX-998877")
    billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("100"), **proof), actor, {})
    with pytest.raises(AppException) as error:
        billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("100"), **proof), actor, {})
    assert error.value.code == "billing_payment_reference_used"
    # The same number at a different provider is a different transaction.
    billing.create_payment(invoice.id, BillingPaymentCreate(amount=Decimal("100"), **{**proof, "payment_provider": "rocket"}), actor, {})


@pytest.mark.parametrize("amount,words", [
    ("0", "Taka Zero Only"), ("15", "Taka Fifteen Only"), ("1250.50", "Taka One Thousand Two Hundred Fifty and Paisa Fifty Only"),
    ("123456.78", "Taka One Lakh Twenty Three Thousand Four Hundred Fifty Six and Paisa Seventy Eight Only"),
    ("10000000", "Taka One Crore Only"), ("250000000.01", "Taka Twenty Five Crore and Paisa One Only"),
])
def test_amount_in_words_uses_lakh_and_crore(amount, words):
    assert amount_in_words(Decimal(amount)) == words
