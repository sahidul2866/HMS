"""One source of truth for the OPD dashboard: every figure is for the same hospital day and the same visits."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models.billing import BillingInvoice
from app.models.encounter import OPDVisit
from app.schemas.encounter import OPDDailyCount, OPDDoctorLoad, OPDLiveQueueItem, OPDSummary

LIVE_QUEUE_LIMIT = 8
QUEUE_STATUSES = ("in_consultation", "waiting")
ZERO = Decimal("0.00")


def hospital_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().hospital_timezone))


def hospital_today() -> date:
    return hospital_now().date()


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def build_summary(db: Session, branch_id, doctor_user_id=None, today: date | None = None) -> OPDSummary:
    now = hospital_now()
    today = today or now.date()
    base = select(OPDVisit)
    if branch_id:
        base = base.where(OPDVisit.branch_id == branch_id)
    if doctor_user_id:
        base = base.where(OPDVisit.consulting_doctor_user_id == doctor_user_id)

    visits = list(db.scalars(base.where(OPDVisit.visit_date == today).options(joinedload(OPDVisit.patient), joinedload(OPDVisit.orders), joinedload(OPDVisit.consulting_doctor))).unique())
    active = [visit for visit in visits if visit.status != "cancelled"]
    by_status = lambda name: sum(1 for visit in visits if visit.status == name)

    invoices = []
    if active:
        invoices = list(db.scalars(select(BillingInvoice).where(BillingInvoice.source_opd_visit_id.in_([visit.id for visit in active]), BillingInvoice.status != "void")))
    consultation_billed = {invoice.source_opd_visit_id for invoice in invoices if invoice.billing_stage == "opd"}
    with_balance = {invoice.source_opd_visit_id for invoice in invoices if Decimal(invoice.due_amount or 0) > 0}

    doctors: dict = {}
    for visit in active:
        if visit.consulting_doctor_user_id:
            name = visit.consulting_doctor.full_name if visit.consulting_doctor else visit.consulting_doctor_name
            row = doctors.setdefault(visit.consulting_doctor_user_id, [name, 0])
            row[1] += 1

    order_count = lambda kind: sum(1 for visit in active for order in visit.orders if order.is_active and order.order_type == kind and order.status != "cancelled")

    first = today - timedelta(days=6)
    daily_stmt = select(OPDVisit.visit_date, func.count(OPDVisit.id)).where(OPDVisit.visit_date >= first, OPDVisit.visit_date <= today, OPDVisit.status != "cancelled").group_by(OPDVisit.visit_date)
    if branch_id:
        daily_stmt = daily_stmt.where(OPDVisit.branch_id == branch_id)
    if doctor_user_id:
        daily_stmt = daily_stmt.where(OPDVisit.consulting_doctor_user_id == doctor_user_id)
    counts = {row[0]: row[1] for row in db.execute(daily_stmt)}

    queue = [visit for visit in active if visit.status in QUEUE_STATUSES]
    queue.sort(key=lambda visit: (QUEUE_STATUSES.index(visit.status), visit.queue_number or "~", visit.created_at))
    first_waiting: set = set()
    live = []
    for visit in queue[:LIVE_QUEUE_LIMIT]:
        if visit.status == "in_consultation":
            action = "With the doctor"
        elif visit.consulting_doctor_user_id not in first_waiting:
            first_waiting.add(visit.consulting_doctor_user_id)
            action = "Next to be called"
        else:
            action = "Waiting"
        started = visit.created_at.astimezone(now.tzinfo) if visit.created_at else now
        live.append(OPDLiveQueueItem(
            visit_id=visit.id, queue_number=visit.queue_number,
            patient_name=f"{visit.patient.first_name} {visit.patient.last_name}".strip(), patient_number=visit.patient.patient_number,
            doctor_name=(visit.consulting_doctor.full_name if visit.consulting_doctor else None) or (visit.consulting_doctor_name if visit.consulting_doctor_user_id else None),
            status=visit.status, payment_status=visit.consultation_payment_status or "unpaid",
            waiting_minutes=max(0, int((now - started).total_seconds() // 60)), next_action=action,
        ))

    return OPDSummary(
        total_visits=len(visits),
        waiting_visits=by_status("waiting"),
        in_consultation_visits=by_status("in_consultation"),
        completed_visits=by_status("completed"),
        summary_date=today,
        as_of=now,
        prescribed_visits=by_status("prescribed"),
        cancelled_visits=by_status("cancelled"),
        not_billed_visits=sum(1 for visit in active if visit.id not in consultation_billed),
        paid_visits=sum(1 for visit in active if visit.consultation_payment_status == "paid"),
        visits_with_balance=len(with_balance),
        gross_amount=_money(sum((Decimal(i.sub_total or 0) + Decimal(i.item_discount_amount or 0) for i in invoices), ZERO)),
        discount_amount=_money(sum((Decimal(i.discount_amount or 0) for i in invoices), ZERO)),
        billed_amount=_money(sum((Decimal(i.total_amount or 0) for i in invoices), ZERO)),
        collected_amount=_money(sum((Decimal(i.paid_amount or 0) - Decimal(i.refunded_amount or 0) for i in invoices), ZERO)),
        outstanding_amount=_money(sum((Decimal(i.due_amount or 0) for i in invoices), ZERO)),
        prescription_orders=order_count("prescription"),
        investigation_orders=order_count("investigation"),
        procedure_orders=order_count("procedure"),
        unassigned_visits=sum(1 for visit in active if not visit.consulting_doctor_user_id),
        doctor_load=[OPDDoctorLoad(doctor_user_id=key, doctor_name=value[0], visits=value[1]) for key, value in sorted(doctors.items(), key=lambda item: (-item[1][1], item[1][0]))],
        daily_visits=[OPDDailyCount(day=first + timedelta(days=offset), visits=counts.get(first + timedelta(days=offset), 0)) for offset in range(7)],
        live_queue=live,
    )
