"""The OPD dashboard shows one hospital day, from one source, with money taken from real invoices."""
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from test_opd_workflow_integration import database, db, seed, visit  # noqa: F401
from app.models.billing import BillingItemConfig
from app.models.encounter import OPDVisit
from app.modules.billing.service import BillingServiceManager
from app.modules.opd.dashboard import build_summary, hospital_now
from app.schemas.billing import BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate


def invoice_for(db, actor, billing, current, patient, pay=None):
    config = db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module == "opd", BillingItemConfig.unit_price == 500))
    invoice = billing.create_invoice(BillingInvoiceCreate(patient_id=patient.id, source_opd_visit_id=current.id, source_module="opd", billing_stage="opd", items=[BillingInvoiceItemCreate(billing_service_id=config.id, quantity=1)]), actor, {})
    if pay:
        invoice = billing.create_payment(invoice.id, BillingPaymentCreate(amount=pay, payment_method="cash"), actor, {})
    return invoice


def test_every_figure_is_for_the_same_day_and_agrees_with_the_invoices(db):
    actor, doctors, patient, slot = seed(db)
    billing = BillingServiceManager(db)
    billing.list_services(actor)
    paid = visit(db, actor, doctors[0], patient, slot)
    part = visit(db, actor, doctors[1], patient, slot + timedelta(minutes=15))
    unbilled = visit(db, actor, doctors[0], patient, slot + timedelta(minutes=30))
    invoice_for(db, actor, billing, paid, patient, pay=Decimal("500"))
    invoice_for(db, actor, billing, part, patient, pay=Decimal("200"))
    old = db.get(OPDVisit, unbilled.id)
    summary = build_summary(db, actor.branch_id, today=slot.date())
    assert summary.total_visits == 3 and summary.waiting_visits == 3
    assert (summary.paid_visits, summary.visits_with_balance, summary.not_billed_visits) == (1, 1, 1)
    assert summary.billed_amount == Decimal("1000.00") and summary.collected_amount == Decimal("700.00") and summary.outstanding_amount == Decimal("300.00")
    assert summary.billed_amount == summary.collected_amount + summary.outstanding_amount
    assert [(row.doctor_name, row.visits) for row in summary.doctor_load] == [("Doctor 0", 2), ("Doctor 1", 1)]
    # The same visits must not count on another day.
    other = build_summary(db, actor.branch_id, today=slot.date() + timedelta(days=1))
    assert other.total_visits == 0 and other.collected_amount == Decimal("0.00") and other.live_queue == []
    assert old is not None


def test_outstanding_is_zero_only_when_nothing_is_owed(db):
    actor, doctors, patient, slot = seed(db)
    billing = BillingServiceManager(db)
    billing.list_services(actor)
    current = visit(db, actor, doctors[0], patient, slot)
    summary = build_summary(db, actor.branch_id, today=slot.date())
    # Registered but not invoiced: nothing is owed yet, and the dashboard says it is "not billed", not "unpaid".
    assert summary.outstanding_amount == Decimal("0.00") and summary.visits_with_balance == 0 and summary.not_billed_visits == 1
    invoice_for(db, actor, billing, current, patient)
    summary = build_summary(db, actor.branch_id, today=slot.date())
    assert summary.outstanding_amount == Decimal("500.00") and summary.visits_with_balance == 1 and summary.not_billed_visits == 0


def test_prescribed_patients_are_counted_apart_from_the_queue(db):
    actor, doctors, patient, slot = seed(db)
    first = visit(db, actor, doctors[0], patient, slot)
    visit(db, actor, doctors[1], patient, slot + timedelta(minutes=15))
    db.get(OPDVisit, first.id).status = "prescribed"
    db.flush()
    summary = build_summary(db, actor.branch_id, today=slot.date())
    assert (summary.prescribed_visits, summary.waiting_visits, summary.in_consultation_visits) == (1, 1, 0)
    assert [item.status for item in summary.live_queue] == ["waiting"]
    assert summary.live_queue[0].next_action == "Next to be called"


def test_a_visit_without_a_doctor_is_not_listed_as_a_doctor(db):
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    row = db.get(OPDVisit, current.id)
    row.consulting_doctor_user_id = None
    row.consulting_doctor_name = "Billing Desk"
    db.flush()
    summary = build_summary(db, actor.branch_id, today=slot.date())
    assert summary.unassigned_visits == 1 and summary.doctor_load == []


def test_trend_ends_on_today_and_cancelled_visits_are_not_traffic(db):
    actor, doctors, patient, slot = seed(db)
    gone = visit(db, actor, doctors[0], patient, slot)
    visit(db, actor, doctors[1], patient, slot + timedelta(minutes=15))
    db.get(OPDVisit, gone.id).status = "cancelled"
    db.flush()
    summary = build_summary(db, actor.branch_id, today=slot.date())
    assert [point.day for point in summary.daily_visits][-1] == slot.date() and len(summary.daily_visits) == 7
    assert summary.daily_visits[-1].visits == 1 and summary.total_visits == 2 and summary.cancelled_visits == 1


def test_today_follows_the_hospital_clock_not_utc():
    assert hospital_now().utcoffset() == timedelta(hours=6)


def test_summary_can_be_asked_for_another_day(db):
    from app.modules.opd.service import OPDService
    actor, doctors, patient, slot = seed(db)
    visit(db, actor, doctors[0], patient, slot)
    assert OPDService(db).get_summary(actor, None, slot.date()).total_visits == 1
    assert OPDService(db).get_summary(actor, None, slot.date() - timedelta(days=3)).total_visits == 0
