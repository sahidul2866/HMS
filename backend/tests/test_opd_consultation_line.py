"""The OPD billing draft must price the consultation from the visit's own doctor, not a fuzzy catalogue match."""
from decimal import Decimal
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import select

from test_opd_workflow_integration import database, db, seed, visit  # noqa: F401
from app.models.billing import BillingItemConfig
from app.modules.billing.service import BillingServiceManager


def consult_config(db, doctor, kind="consult"):
    return db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module == "opd", BillingItemConfig.source_entity_id == uuid5(NAMESPACE_DNS, f"opd:{doctor.id}:{kind}")))


def consultation_line(db, actor, current):
    draft = BillingServiceManager(db).build_opd_visit_draft(current.id, actor)
    return next(item for item in draft.items if item.source_module == "opd_visit")


def test_each_doctor_visit_is_priced_from_that_doctors_consultation_fee(db):
    actor, doctors, patient, slot = seed(db)
    doctors[1].opd_consultation_fee = Decimal("500")  # same fee as the other doctor; only the owner tells them apart
    db.flush()
    billing = BillingServiceManager(db)
    billing.list_services(actor)
    current = visit(db, actor, doctors[1], patient, slot)
    assert consultation_line(db, actor, current).billing_service_id == consult_config(db, doctors[1]).id


def test_zero_fee_doctor_is_not_billed_as_an_unrelated_free_item(db):
    actor, doctors, patient, slot = seed(db)
    doctors[0].opd_consultation_fee = Decimal("0")
    db.add(BillingItemConfig(branch_id=actor.branch_id, source_module="inventory", source_entity_id=doctors[0].id, service_code="INV-STRAY", service_name="Stray Medicine kit", unit_price=Decimal("0")))
    db.flush()
    BillingServiceManager(db).list_services(actor)
    current = visit(db, actor, doctors[0], patient, slot)
    line = consultation_line(db, actor, current)
    assert line.billing_service_id == consult_config(db, doctors[0]).id
    assert "Stray" not in (line.billing_service_name or "")
