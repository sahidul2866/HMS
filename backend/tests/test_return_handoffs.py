"""Return credit, cash and departmental cancellation must commit as one operation."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_billing_review_probes import make, interim_final
from test_opd_workflow_integration import database, db  # noqa: F401
from app.core.exceptions import AppException
from app.models.billing import BillingItemConfig
from app.models.encounter import OPDVisit, OPDVisitOrder
from app.models.laboratory import LabOrder, LabOrderItem
from app.modules.billing.operations import BillingOperations
from app.modules.laboratory.service import LaboratoryService
from app.schemas.billing import BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate, BillingReturnCreate, BillingReturnItemCreate, BillingInvoiceRead
from app.schemas.encounter import ClinicalInvestigationResultUpdate


def credit(service, invoice, actor, quantity):
    return service.create_return(invoice.id, BillingReturnCreate(reason='Unused charge cancelled', items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id, quantity=quantity)]), actor, {})


@pytest.mark.parametrize('paid,quantity,due,payout', [(0,1,100,0),(20,1,80,0),(150,1,0,50),(20,2,0,20)])
def test_credit_reduces_debt_before_any_cash_is_paid_back(db, paid, quantity, due, payout):
    actor, _, patient, service, config = make(db, 100)
    invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=2)]), actor, {})
    if paid:
        invoice = service.create_payment(invoice.id, BillingPaymentCreate(amount=paid,payment_method='cash'), actor, {})
    invoice = credit(service, invoice, actor, quantity)
    assert invoice.due_amount == due
    assert invoice.paid_amount == paid-payout
    assert invoice.credited_amount == 100*quantity and invoice.net_payable_amount == 200-100*quantity
    assert invoice.refunds[0].credit_amount == 100*quantity
    assert invoice.refunds[0].amount == payout
    assert BillingInvoiceRead.model_validate(invoice).items[0].returnable_quantity == 2-quantity
    custody = BillingOperations(db).cash_balance(actor)
    assert custody['expected_amount'] == paid-payout
    assert custody['refund_count'] == (1 if payout else 0)
    stats = BillingOperations(db).statistics(actor)
    assert Decimal(stats['totals']['returned']) == 100*quantity
    assert Decimal(stats['totals']['refunded']) == payout
    assert Decimal(stats['totals']['net']) == 200-100*quantity


def test_final_invoice_keeps_return_payouts_without_double_credit(db):
    actor, service, interim_for, final_for, *_ = interim_final(db)
    interim = interim_for(10)
    interim = service.create_payment(interim.id, BillingPaymentCreate(amount=1000,payment_method='cash'), actor, {})
    credit(service, interim, actor, 4)
    final = final_for()
    assert final.total_amount == 600 and final.paid_amount == 600 and final.refunded_amount == 400
    assert sum((p.amount for p in final.payments), Decimal(0))-sum((r.amount for r in final.refunds),Decimal(0)) == final.paid_amount
    assert final.refunds[0].refund_type == 'carried_return'
    assert final.refunds[0].return_items[0]['original_invoice_id'] == str(interim.id)
    stats = BillingOperations(db).statistics(actor)
    assert Decimal(stats['totals']['collected'])-Decimal(stats['totals']['refunded']) == 600
    assert Decimal(stats['totals']['net']) == 600


def clinical_bill(db):
    actor, _, patient, service, config = make(db, 100)
    visit = OPDVisit(branch_id=actor.branch_id, patient_id=patient.id, visit_number='RETURN-'+uuid4().hex[:12], visit_date=datetime.now(UTC).date(), department_name='Review', consulting_doctor_name='Review doctor', registered_by_user_id=actor.id)
    db.add(visit);db.flush()
    domain = LabOrder(branch_id=actor.branch_id,patient_id=patient.id,visit_id=visit.id,order_number='LAB-'+uuid4().hex[:12],status='pending')
    db.add(domain);db.flush()
    db.add(LabOrderItem(order_id=domain.id,test_name='Unused test',quantity=1));db.flush()
    order = OPDVisitOrder(visit_id=visit.id,order_type='investigation',service_area='laboratory',item_name='Unused test',quantity=1,status='pending',lab_order_id=domain.id)
    db.add(order);db.flush()
    db.get(BillingItemConfig,config['id']).source_module='laboratory';db.flush()
    invoice=service.create_invoice(BillingInvoiceCreate(patient_id=patient.id,source_opd_visit_id=visit.id,items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1,source_opd_visit_order_id=order.id)]),actor,{})
    return actor, service, invoice, order, domain


def test_unused_lab_return_cancels_work_and_cannot_be_reopened(db):
    actor, service, invoice, order, domain = clinical_bill(db)
    invoice=credit(service,invoice,actor,1)
    assert order.status == 'cancelled' and domain.status == 'cancelled'
    with pytest.raises(AppException) as error:
        LaboratoryService(db).update_result(domain.id,ClinicalInvestigationResultUpdate(status='completed'),actor,{})
    assert error.value.code == 'clinical_order_cancelled'


def test_started_lab_return_is_rejected_without_changing_the_invoice(db):
    actor, service, invoice, order, domain = clinical_bill(db)
    domain.collected_at=datetime.now(UTC);domain.status='collected';db.commit()
    with pytest.raises(AppException) as error:
        credit(service,invoice,actor,1)
    assert error.value.code == 'billing_return_fulfilled'
    assert order.status == 'pending' and domain.status == 'collected'
    assert invoice.due_amount == 100 and not invoice.refunds


def test_void_unused_invoice_clears_debt_and_preserves_original_charge(db):
    from app.schemas.billing import BillingInvoiceVoidRequest
    actor, _, patient, service, config = make(db, 100)
    invoice = service.create_invoice(BillingInvoiceCreate(patient_id=patient.id, items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1)]), actor, {})
    invoice = service.void_invoice(invoice.id, BillingInvoiceVoidRequest(reason='Synthetic unused invoice cancelled'), actor, {})
    assert invoice.status == 'void' and invoice.payment_status == 'void'
    assert invoice.total_amount == 100 and invoice.net_payable_amount == 0 and invoice.due_amount == 0
    assert not invoice.payments and not invoice.refunds


def test_unused_ipd_cancellation_clears_only_its_pending_doses_and_tasks():
    from types import SimpleNamespace
    from app.models.encounter import IPDAdmission, IPDOrder, IPDMedicationAdministration, IPDNursingTask
    from app.modules.billing.return_fulfilment import cancel_unused
    actor=SimpleNamespace(id=uuid4())
    admission=IPDAdmission()
    order=IPDOrder(id=uuid4(),admission=admission,status='ordered')
    due=IPDMedicationAdministration(order_id=order.id,status='due')
    administered=IPDMedicationAdministration(order_id=order.id,status='administered')
    other=IPDMedicationAdministration(order_id=uuid4(),status='due')
    admission.medication_administrations=[due,administered,other]
    task=IPDNursingTask(status='overdue');order.nursing_tasks=[task]
    cancel_unused([order],actor)
    assert order.status=='cancelled' and order.billing_status=='returned'
    assert due.status=='skipped' and task.status=='cancelled'
    assert administered.status=='administered' and other.status=='due'
