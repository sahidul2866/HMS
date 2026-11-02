"""Discount corrections, credited returns and cashier custody must reconcile."""
from decimal import Decimal
from datetime import date,datetime,UTC
from uuid import uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from test_opd_workflow_integration import database, db, seed  # noqa: F401
from app.core.exceptions import AppException
from app.models.user import User
from app.models.billing import BillingEvent, BillingReportSnapshot, BillingCashHandoverEntry, BillingItemConfig
from app.modules.billing.service import BillingServiceManager
from app.modules.billing.operations import BillingOperations
from app.schemas.billing import (BillingTypeCreate,BillingInvoiceCreate,BillingInvoiceItemCreate,BillingInvoiceAmend,
    BillingPaymentCreate,BillingRefundCreate,BillingReturnCreate,BillingReturnItemCreate,BillingHandoverCreate,BillingHandoverAccept,BillingServiceCreate)
from app.schemas.pharmacy import PharmacyDispenseCreate


def invoice_fixture(db):
    actor,_,patient,_=seed(db)
    operations=BillingOperations(db);service=BillingServiceManager(db)
    kind=operations.create_type(BillingTypeCreate(code='LAB',name='Diagnostic billing',department='Pathology'),actor)
    config=service.create_service(BillingServiceCreate(service_code='CUSTOM',name='Synthetic service',unit_price=100,doctor_share_percentage=0,billing_type_id=kind.id,max_discount_percentage=20),actor,{})
    invoice=service.create_invoice(BillingInvoiceCreate(patient_id=patient.id,billing_type_id=kind.id,discount_reason='Synthetic approved concession',discount_percentage=10,items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=2,discount_percentage=10)]),actor,{})
    return actor,operations,service,invoice,kind


def test_discount_amendment_history_report_and_item_snapshot(db):
    actor,ops,service,invoice,kind=invoice_fixture(db)
    with pytest.raises(AppException,match='discount reason'):
        service.create_invoice(BillingInvoiceCreate(patient_id=invoice.patient_id,discount_percentage=10,items=[BillingInvoiceItemCreate(billing_service_id=uuid4(),quantity=1)]),actor,{})
    assert invoice.billed_by_name==actor.full_name
    assert invoice.total_amount==Decimal('162.00')
    assert invoice.items[0].billing_department=='Pathology'
    invoice=ops.amend(invoice.id,BillingInvoiceAmend(discount_percentage=20,reason='Supervisor approved concession',note='Corrected note'),actor)
    assert invoice.total_amount==144 and invoice.discount_amount==56
    history=ops.history(invoice.id,actor)
    assert [h.kind for h in history]==['invoice_created','amendment']
    assert history[-1].snapshot['before']['total_amount']=='162.00'
    assert history[-1].snapshot['after']['total_amount']=='144.00'
    kind.department='Renamed department';db.flush()
    assert invoice.billing_department=='Pathology'
    report=ops.statistics(actor)
    assert Decimal(report['totals']['discount'])==56
    assert Decimal(report['departments']['Pathology']['net'])==144
    assert db.get(BillingReportSnapshot,report['snapshot_id']) is not None
    service.create_payment(invoice.id,BillingPaymentCreate(amount=144,payment_method='cash'),actor,{})
    with pytest.raises(AppException,match='Refund the excess'):
        ops.amend(invoice.id,BillingInvoiceAmend(discount_percentage=30,reason='Overpaid reduction rejected'),actor)
    with pytest.raises(AppException,match='Start date'):
        ops.statistics(actor,date(2026,2,2),date(2026,1,1))


def test_return_credits_due_and_cannot_return_same_quantity_twice(db):
    actor,ops,service,invoice,_=invoice_fixture(db)
    invoice=service.create_payment(invoice.id,BillingPaymentCreate(amount=162,payment_method='cash'),actor,{})
    item_id=invoice.items[0].id
    invoice=service.create_return(invoice.id,BillingReturnCreate(reason='Synthetic unused service return',items=[BillingReturnItemCreate(invoice_item_id=item_id,quantity=1)]),actor,{})
    assert invoice.refunded_amount==81 and invoice.paid_amount==81
    assert invoice.due_amount==0 and invoice.payment_status=='paid'
    with pytest.raises(AppException,match='Return quantity'):
        service.create_return(invoice.id,BillingReturnCreate(reason='Duplicate units must fail',items=[BillingReturnItemCreate(invoice_item_id=item_id,quantity=2)]),actor,{})
    # A financial correction cannot silently rewrite a credited invoice.
    with pytest.raises(AppException,match='original discount'):
        ops.amend(invoice.id,BillingInvoiceAmend(reason='Blocked discount edit',discount_percentage=5),actor)


def test_cash_handover_excludes_card_and_requires_independent_acknowledgment(db):
    actor,ops,service,invoice,_=invoice_fixture(db)
    receiver=User(branch_id=actor.branch_id,username='receiver',email='receiver@example.test',full_name='Receiving Supervisor',hashed_password='unused',direct_permissions=list(actor.direct_permissions))
    db.add(receiver);db.flush()
    service.create_payment(invoice.id,BillingPaymentCreate(amount=100,payment_method='cash'),actor,{})
    service.create_payment(invoice.id,BillingPaymentCreate(amount=62,payment_method='card',reference_number='TEST-CARD-0062'),actor,{})
    service.create_refund(invoice.id,BillingRefundCreate(amount=20,payment_method='card',reason='Synthetic card reversal'),actor,{})
    assert ops.cash_balance(actor)['expected_amount']==100
    handover=ops.submit_handover(BillingHandoverCreate(receiver_id=receiver.id,declared_amount=95,note='Five taka cash discrepancy'),actor)
    assert handover.variance==-5 and handover.status=='submitted'
    assert ops.cash_balance(actor)['expected_amount']==0
    assert len(list(db.scalars(select(BillingCashHandoverEntry))))==1
    with pytest.raises(AppException,match='No unsettled'):
        ops.submit_handover(BillingHandoverCreate(receiver_id=receiver.id,declared_amount=0,note='Duplicate shift'),actor)
    with pytest.raises(AppException,match='designated receiver'):
        ops.accept_handover(handover.id,BillingHandoverAccept(note='Self acknowledgment blocked'),actor)
    assert ops.accept_handover(handover.id,BillingHandoverAccept(note='Counted 95; recorded variance'),receiver).status=='accepted'
    with pytest.raises(AppException,match='already accepted'):
        ops.accept_handover(handover.id,BillingHandoverAccept(note='Second acknowledgment blocked'),receiver)


def test_pharmacy_rejects_negative_quantity_and_price():
    for changes in ({'quantity':0},{'quantity':-1},{'unit_price':-1}):
        with pytest.raises(ValidationError):
            PharmacyDispenseCreate(**({'medicine_name':'Test medication','quantity':1,'unit_price':10}|changes))


def test_prescription_dispense_deducts_stock_and_keeps_patient_and_billing_links(db):
    from test_opd_workflow_integration import visit
    from app.models.pharmacy import PharmacyMedicineType,PharmacyGeneric,PharmacyCompany,PharmacyMedicine
    from app.models.encounter import OPDVisitOrder
    from app.models.billing import BillingInvoice
    from app.modules.pharmacy.service import PharmacyService
    actor,doctors,patient,slot=seed(db)
    current=visit(db,actor,doctors[0],patient,slot)
    medicine_type=PharmacyMedicineType(name='ERP Tablet');generic=PharmacyGeneric(name='ERP Generic');company=PharmacyCompany(name='ERP Company')
    db.add_all([medicine_type,generic,company]);db.flush()
    medicine=PharmacyMedicine(branch_id=actor.branch_id,name='ERP Dispense Medicine',medicine_type_id=medicine_type.id,generic_id=generic.id,company_id=company.id,stock_quantity=10,sale_price=20)
    order=OPDVisitOrder(visit_id=current.id,order_type='prescription',item_name=medicine.name,quantity=2,status='pending')
    db.add_all([medicine,order]);db.flush()
    pharmacy=PharmacyService(db)
    with pytest.raises(AppException,match='patient and visit'):
        pharmacy.dispense(PharmacyDispenseCreate(patient_id=uuid4(),source_visit_order_id=order.id,medicine_name=medicine.name,quantity=2,unit_price=20),actor,{})
    dispense=pharmacy.dispense(PharmacyDispenseCreate(patient_id=patient.id,source_visit_order_id=order.id,medicine_name=medicine.name,quantity=2,unit_price=20),actor,{})
    assert medicine.stock_quantity==8 and order.status=='completed'
    invoice=db.get(BillingInvoice,dispense.billing_invoice_id)
    assert invoice.patient_id==patient.id and invoice.total_amount==40
    assert dispense.source_visit_order_id==order.id
    with pytest.raises(AppException,match='no remaining'):
        pharmacy.dispense(PharmacyDispenseCreate(source_visit_order_id=order.id,medicine_name=medicine.name,quantity=1,unit_price=20),actor,{})


def test_parallel_notification_refresh_and_catalog_ids_are_durable(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import text,func
    from sqlalchemy.orm import Session
    from app.models.base import Base
    from app.models.encounter import IPDBed
    from app.models.notification import Notification
    from app.modules.notifications.service import NotificationsService
    from app.modules.ipd.service import IPDService
    from app.schemas.encounter import IPDAdmissionCreate
    schema='billing_race_'+uuid4().hex
    with database.engine.begin() as connection:connection.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    try:
        with Session(engine,expire_on_commit=False) as session:
            actor,doctors,patient,_=seed(session);actor_id=actor.id
            bed=IPDBed(branch_id=actor.branch_id,ward_name='Race Ward',bed_number='RACE',bed_type='General',daily_rate=100,status='available')
            session.add(bed);session.flush()
            IPDService(session).create_admission(IPDAdmissionCreate(patient_id=patient.id,admitted_at=datetime.now(UTC),admission_type="General",bed_id=bed.id,ward_name=bed.ward_name,bed_number=bed.bed_number,attending_doctor_name=doctors[0].full_name),actor,{})
        barrier=Barrier(2)
        def refresh(_):
            with Session(engine,expire_on_commit=False) as session:
                actor=session.get(User,actor_id);barrier.wait(timeout=10)
                NotificationsService(session).summary(actor)
                return BillingServiceManager(session).list_services(actor)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(refresh,range(2)))
        with Session(engine) as session:
            assert all(session.get(BillingItemConfig,item['id']) for batch in results for item in batch)
            assert session.scalar(select(func.count(Notification.id)))>0
    finally:
        with database.engine.begin() as connection:connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
