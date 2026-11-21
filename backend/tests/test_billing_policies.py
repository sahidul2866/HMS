"""Exact financial calculations and persisted policy/settlement workflows."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from types import SimpleNamespace as NS
from uuid import uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from test_opd_workflow_integration import database, db, seed  # noqa: F401
from app.core.exceptions import AppException
from app.models.billing_policy import BillingAllocation, BillingPolicy, BillingCommand
from app.modules.billing.policies import FinancialPolicies, allocate, financial_values, enforce_discount
from app.modules.billing.service import BillingServiceManager
from app.schemas.billing_policy import FinancialRules, PolicyCreate, SettlementCreate
from app.schemas.billing import BillingServiceCreate, BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate, BillingReturnCreate, BillingReturnItemCreate, BillingRefundCreate


def line(gross='1000', discount='200'):
    return NS(unit_price=D(gross), quantity=D(1), discount_amount=D(discount))


@pytest.mark.parametrize('sharing', [ {'hospital':100}, {'doctor':100}, {'agent':100}, {'hospital':50,'doctor':50}, {'hospital':70,'doctor':30}, {'hospital':30,'doctor':70}, {'hospital':40,'doctor':35,'agent':25} ])
def test_discount_responsibility_is_separate_and_exact(sharing):
    rules=FinancialRules(doctor_key='doctor', doctor_revenue_percentage=30, discount_sharing=sharing, participants=[{'key':'agent','name':'Agent','kind':'agent','share':100}])
    values=financial_values(line(),D(800),rules)
    assert sum(values.values())==800
    for key, percentage in sharing.items():
        assert values[(key,'discount')]==-D(200)*percentage/100


def test_doctor_funded_consultation_example():
    rules=FinancialRules(doctor_key='doctor',doctor_revenue_percentage=70,discount_sharing={'doctor':100})
    values=financial_values(line('800','100'),D(700),rules)
    assert values[('doctor','revenue')]+values[('doctor','discount')]==460
    assert values[('hospital','revenue')]==240


@pytest.mark.parametrize('weights', [{'a':1,'b':1,'c':1}, {'a':70,'b':30}, {'a':0,'b':100}, {str(i):1 for i in range(300)}])
@pytest.mark.parametrize('amount', ['0.00','0.01','0.02','100.01','999999.99'])
def test_paisa_allocation(weights,amount):
    result=allocate(D(amount),{k:D(v) for k,v in weights.items()})
    assert sum(result.values())==D(amount)
    assert all(v>=0 for v in result.values())
    assert result==allocate(D(amount),dict(reversed(list((k,D(v)) for k,v in weights.items()))))


@pytest.mark.parametrize('basis,expected',[('gross',100),('net',80)])
@pytest.mark.parametrize('split',[(50,50),(70,30),(30,70)])
def test_multiple_referral_participants_and_basis(basis,expected,split):
    rules=FinancialRules(commission_enabled=True,commission_basis=basis,commission_percentage=10,participants=[{'key':'a','name':'Doctor','kind':'doctor','share':split[0]},{'key':'b','name':'Pharmacy','kind':'pharmacy','share':split[1]}])
    values=financial_values(line(),D(800),rules)
    assert values[('a','commission')]==D(expected)*split[0]/100
    assert values[('b','commission')]==D(expected)*split[1]/100
    assert sum(values.values())==800


@pytest.mark.parametrize('changes',[{'discount_sharing':{'hospital':99}}, {'discount_sharing':{'hospital':110,'x':-10}}, {'commission_enabled':True}, {'doctor_revenue_percentage':70}, {'discount_sharing':{'unknown':100}}, {'commission_enabled':True,'commission_fixed':10,'commission_percentage':1}])
def test_invalid_financial_configuration(changes):
    with pytest.raises(ValidationError): FinancialRules(**changes)


@pytest.mark.parametrize('rules,item_discount,invoice_discount', [({'discounts_allowed':False},0,1),({'max_percentage':20},100,101),({'max_amount':100},100,1),({'combine':False},1,1)])
def test_invoice_discount_cannot_bypass_service_restrictions(rules,item_discount,invoice_discount):
    with pytest.raises(AppException): enforce_discount(line(discount=str(item_discount)),D(invoice_discount),FinancialRules(**rules))


def test_discount_roles_and_approval():
    actor=NS(roles=[NS(code='CASHIER',is_active=True)])
    with pytest.raises(AppException): enforce_discount(line(),D(0),FinancialRules(allowed_roles=['MANAGER']),actor,True)
    with pytest.raises(AppException): enforce_discount(line(),D(0),FinancialRules(approval_required=True),actor,False)
    enforce_discount(line(),D(0),FinancialRules(approval_required=True,allowed_roles=['CASHIER']),actor,True)


def setup_invoice(db, rules=None, quantity=2, discount=10, paid=0):
    actor,doctors,patient,slot=seed(db)
    service=BillingServiceManager(db); policies=FinancialPolicies(db)
    config=service.create_service(BillingServiceCreate(service_code='POLICY',name='Policy investigation',unit_price=1000,doctor_share_percentage=0),actor,{})
    rules=rules or FinancialRules(doctor_key='doctor',doctor_revenue_percentage=30,discount_sharing={'hospital':50,'doctor':50})
    policy=policies.create(PolicyCreate(scope='item',selector=str(config['id']),effective_from=datetime.now(UTC)-timedelta(days=1),reason='Approved test policy',rules=rules),actor)
    invoice=service.create_invoice(BillingInvoiceCreate(patient_id=patient.id,discount_percentage=discount,discount_reason='Approved concession',items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=quantity)]),actor,{})
    if paid: invoice=service.create_payment(invoice.id,BillingPaymentCreate(amount=paid,payment_method='cash',request_key='initial-payment'),actor,{})
    return actor,service,policies,invoice,config,policy


@pytest.mark.parametrize('paid,expected_payout,expected_due',[(0,0,900),(500,0,400),(1000,100,0),(1800,900,0)])
def test_persisted_partial_returns_reconcile(db,paid,expected_payout,expected_due):
    actor,service,policies,invoice,_,_=setup_invoice(db,paid=paid)
    invoice=service.create_return(invoice.id,BillingReturnCreate(items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=1)],reason='Unused investigation',request_key='return-first'),actor,{})
    assert invoice.refunded_amount==expected_payout and invoice.due_amount==expected_due
    rows=policies.entries(actor)
    assert sum(r.amount for r in rows)==900
    assert sum(r.amount for r in rows if r.participant_key=='doctor')==250
    assert len(list(db.scalars(select(BillingCommand))))==int(bool(paid))+1


def test_settlement_then_return_produces_recoverable_adjustment(db):
    actor,service,policies,invoice,_,_=setup_invoice(db,paid=1800)
    payload=SettlementCreate(participant_key='doctor',amount=500,request_key='settlement-001',reason='Doctor payout')
    settled=policies.settle(payload,actor)
    assert policies.settle(payload,actor).id==settled.id
    invoice=service.create_return(invoice.id,BillingReturnCreate(items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=2)],reason='All investigations cancelled',request_key='cancel-all-items'),actor,{})
    rows=policies.entries(actor)
    assert db.get(BillingAllocation,settled.id).amount==-500
    assert sum(r.amount for r in rows if r.participant_key=='doctor')==-500
    assert invoice.refunded_amount==1800 and invoice.net_payable_amount==0
    with pytest.raises(AppException): policies.settle(SettlementCreate(participant_key='doctor',amount=1,request_key='settlement-002',reason='Invalid payout'),actor)


def test_historical_snapshot_survives_new_policy_and_repeated_requests(db):
    actor,service,policies,invoice,config,old=setup_invoice(db,paid=1800)
    frozen=invoice.items[0].financial_snapshot
    policies.create(PolicyCreate(scope='item',selector=str(config['id']),effective_from=datetime.now(UTC),reason='New responsibility policy',rules=FinancialRules(discounts_allowed=False)),actor)
    assert invoice.items[0].financial_snapshot==frozen and frozen['policy_id']==str(old.id)
    payload=BillingReturnCreate(items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=1)],reason='First unused unit',request_key='duplicate-return')
    first=service.create_return(invoice.id,payload,actor,{})
    second=service.create_return(invoice.id,payload,actor,{})
    assert first.refunded_amount==second.refunded_amount==900 and len(second.refunds)==1
    with pytest.raises(AppException): service.create_return(invoice.id,payload.model_copy(update={'reason':'Different content'}),actor,{})


def test_multiple_refunds_and_payment_retries(db):
    actor,service,policies,invoice,_,_=setup_invoice(db,paid=1800)
    assert service.create_payment(invoice.id,BillingPaymentCreate(amount=1800,payment_method='cash',request_key='initial-payment'),actor,{}).paid_amount==1800
    for index in range(3):
        p=BillingRefundCreate(amount=100,reason='Payment reversal',request_key=f'refund-request-{index}')
        service.create_refund(invoice.id,p,actor,{})
        service.create_refund(invoice.id,p,actor,{})
    assert invoice.paid_amount==1500 and invoice.refunded_amount==300 and len(invoice.refunds)==3
    assert sum(r.amount for r in policies.entries(actor))==1800 # cash reversal retains service receivable
    with pytest.raises(AppException): service.create_refund(invoice.id,BillingRefundCreate(amount=1501,reason='Excess refund'),actor,{})


def test_pending_commission_approval_and_limits(db):
    rules=FinancialRules(commission_enabled=True,commission_percentage=10,commission_approval_required=True,participants=[{'key':'agent','name':'External agent','kind':'agent','share':100}])
    actor,service,policies,invoice,_,_=setup_invoice(db,rules=rules)
    with pytest.raises(AppException): policies.settle(SettlementCreate(participant_key='agent',amount=180,request_key='pending-settle',reason='Needs approval'),actor)
    row=policies.settle(SettlementCreate(participant_key='agent',amount=180,request_key='approved-settle',reason='Supervisor approved',approve_pending=True),actor)
    assert row.state=='settled'
    assert sum(r.amount for r in policies.entries(actor) if r.participant_key=='agent')==0


def test_disabled_commission_and_fixed_hospital_deduction():
    values=financial_values(line('800','100'),D(700),FinancialRules(doctor_key='dr',hospital_fixed_deduction=240,discount_sharing={'dr':100}))
    assert values[('dr','revenue')]+values[('dr','discount')]==460
    assert not any(component=='commission' for _,component in values)


def test_effective_dates_and_policy_precedence(db):
    actor,service,policies,invoice,config,old=setup_invoice(db)
    future=policies.create(PolicyCreate(scope='item',selector=str(config['id']),effective_from=datetime.now(UTC)+timedelta(days=1),reason='Future policy',rules=FinancialRules()),actor)
    policies.create(PolicyCreate(scope='hospital',effective_from=datetime.now(UTC)-timedelta(days=1),reason='Hospital default',rules=FinancialRules()),actor)
    from app.models.billing import BillingItemConfig
    assert policies.resolve(actor,db.get(BillingItemConfig,config['id']),invoice)['policy_id']==str(old.id)
    assert future.id!=old.id


@pytest.mark.parametrize('paid',[0,500,1800])
def test_full_cancellation_is_atomic_and_retains_original(db,paid):
    from app.schemas.billing import BillingInvoiceCancelRequest
    actor,service,policies,invoice,_,_=setup_invoice(db,paid=paid)
    payload=BillingInvoiceCancelRequest(reason='Full unused invoice cancellation',request_key='cancel-full-invoice')
    cancelled=service.cancel_invoice(invoice.id,payload,actor,{})
    assert cancelled.status=='void' and cancelled.due_amount==0
    assert cancelled.total_amount==1800 and cancelled.refunded_amount==paid
    assert cancelled.paid_amount==0 and len(cancelled.items)==1
    assert sum(r.amount for r in policies.entries(actor))==0
    assert service.cancel_invoice(invoice.id,payload,actor,{}).id==cancelled.id


def test_api_policy_invoice_payment_cancel_and_history(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    actor,service,policies,invoice,config,_=setup_invoice(db,paid=1800)
    original=app.dependency_overrides.copy()
    app.dependency_overrides[get_db]=lambda: db
    app.dependency_overrides[get_current_user]=lambda: actor
    try:
        client=TestClient(app)
        response=client.get('/api/v1/billing/policies')
        assert response.status_code==200 and len(response.json())==1
        payload={'reason':'API full cancellation','request_key':'api-cancel-0001','payment_method':'cash'}
        for _ in range(2):
            response=client.post(f'/api/v1/billing/invoices/{invoice.id}/cancel',json=payload)
            assert response.status_code==200,response.text
            assert response.json()['status']=='void' and D(response.json()['refunded_amount'])==1800
        response=client.get(f'/api/v1/billing/invoices/{invoice.id}/history')
        assert response.status_code==200
        assert [r['kind'] for r in response.json()]==['invoice_created','payment_collected','items_returned','invoice_voided']
        assert len(policies.entries(actor))>0
        bad=client.post('/api/v1/billing/policies',json={'scope':'hospital','effective_from':datetime.now(UTC).isoformat(),'reason':'Invalid allocation','rules':{'discount_sharing':{'hospital':'99'}}})
        assert bad.status_code==422
    finally:
        app.dependency_overrides=original


@pytest.mark.parametrize('same_key',[True,False])
def test_concurrent_refunds_are_serialized(database,same_key):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from app.models.base import Base
    from app.models.user import User
    from app.models.billing import BillingInvoice, BillingRefund
    schema='financial_race_'+uuid4().hex
    with database.engine.begin() as conn: conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    try:
        with Session(engine,expire_on_commit=False) as session:
            actor,service,policies,invoice,_,_=setup_invoice(session,paid=1800)
            actor_id=actor.id; invoice_id=invoice.id
        barrier=Barrier(2)
        def refund(index):
            with Session(engine,expire_on_commit=False) as session:
                actor=session.get(User,actor_id)
                barrier.wait(timeout=10)
                try:
                    BillingServiceManager(session).create_refund(invoice_id,BillingRefundCreate(amount=1000,reason='Concurrent audited refund',request_key='concurrent-same' if same_key else f'concurrent-{index}'),actor,{})
                    return 'ok'
                except AppException:
                    session.rollback();return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(refund,range(2)))
        assert results.count('ok')==(2 if same_key else 1)
        with Session(engine) as session:
            persisted=session.get(BillingInvoice,invoice_id)
            assert persisted.refunded_amount==1000 and persisted.paid_amount==800
            assert len(list(session.scalars(select(BillingRefund))))==1
    finally:
        with database.engine.begin() as conn: conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_migration_upgrade_immutability_and_downgrade(database):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text, inspect
    from sqlalchemy.exc import DBAPIError
    from app.models.base import Base
    schema='policy_migration_'+uuid4().hex
    with database.engine.begin() as conn: conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema})
    existing=[table for table in Base.metadata.sorted_tables if table.name not in {'billing_policies','billing_allocations','billing_commands'}]
    Base.metadata.create_all(engine,tables=existing)
    spec=importlib.util.spec_from_file_location('billing_policy_migration',Path(__file__).parents[1]/'alembic/versions/20261119_0076_billing_policies.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    try:
        with engine.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO {schema}'))
            conn.execute(text('ALTER TABLE billing_invoice_items DROP COLUMN financial_snapshot'))
            conn.execute(text('ALTER TABLE referred_doctors DROP COLUMN referrer_type'))
            with Operations.context(MigrationContext.configure(conn)):
                module.upgrade()
            assert 'billing_policies' in inspect(conn).get_table_names(schema=schema)
            conn.execute(text("INSERT INTO billing_policies(id,scope,selector,effective_from,reason,rules) VALUES (:id,'hospital','*',now(),'Migration test','{}')"),{'id':uuid4()})
            with conn.begin_nested() as savepoint:
                with pytest.raises(DBAPIError,match='append-only'):
                    conn.execute(text("UPDATE billing_policies SET reason='Mutated'"))
                savepoint.rollback()
            with Operations.context(MigrationContext.configure(conn)):
                module.downgrade()
            assert 'billing_policies' not in inspect(conn).get_table_names(schema=schema)
    finally:
        with database.engine.begin() as conn: conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_default_discount_free_fee_and_approved_override(db):
    actor,service,policies,invoice,config,_=setup_invoice(db,rules=FinancialRules(default_discount_percentage=15),discount=0)
    assert invoice.total_amount==1700 and invoice.items[0].discount_amount==300
    free=service.create_invoice(BillingInvoiceCreate(patient_id=invoice.patient_id,items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1,unit_price_override=0,override_reason='Authorized free consultation')]),actor,{})
    assert free.total_amount==0 and free.payment_status=='paid'
    assert 'Authorized free consultation' in free.items[0].source_label
    long_reason = 'Approved exceptional concession: ' + 'x' * 400
    revised = service.create_invoice(BillingInvoiceCreate(patient_id=invoice.patient_id,items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1,unit_price_override=0,override_reason=long_reason)]),actor,{})
    assert len(revised.items[0].source_label)<=180
    assert revised.items[0].financial_snapshot['fee_override']['reason']==long_reason


def test_legacy_catalog_item_restriction_cannot_be_bypassed(db):
    actor,_,patient,_=seed(db); service=BillingServiceManager(db)
    config=service.create_service(BillingServiceCreate(service_code='NO-DISC',name='Restricted service',unit_price=100,doctor_share_percentage=0,max_discount_percentage=0),actor,{})
    with pytest.raises(AppException,match='Combined'):
        service.create_invoice(BillingInvoiceCreate(patient_id=patient.id,discount_percentage=10,discount_reason='Invoice bypass attempt',items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1)]),actor,{})


def test_external_referrer_registration_and_invoice_identity(db):
    from app.schemas.billing import ReferredDoctorCreate
    actor,service,policies,invoice,config,_=setup_invoice(db)
    referrer=service.create_doctor(ReferredDoctorCreate(doctor_code='PHARM-01',full_name='Registered Pharmacy',referrer_type='pharmacy'),actor,{})
    policies.create(PolicyCreate(scope='referrer',selector=str(referrer.id),effective_from=datetime.now(UTC)-timedelta(days=1),reason='Approved pharmacy arrangement',rules=FinancialRules(commission_enabled=True,commission_percentage=5,participants=[{'key':str(referrer.id),'name':referrer.full_name,'kind':'pharmacy','share':100}])),actor)
    billed=service.create_invoice(BillingInvoiceCreate(patient_id=invoice.patient_id,referred_doctor_id=referrer.id,items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1)]),actor,{})
    assert billed.referred_doctor_id==referrer.id and billed.referred_doctor_name==referrer.full_name
    # The item policy has higher precedence than the referral policy.
    assert billed.items[0].financial_snapshot['policy_id']==invoice.items[0].financial_snapshot['policy_id']


def test_small_line_rounding_is_frozen_and_never_negative(db):
    actor,_,patient,_=seed(db);service=BillingServiceManager(db)
    config=service.create_service(BillingServiceCreate(service_code='PAISA',name='Small service',unit_price=D('.01'),doctor_share_percentage=0),actor,{})
    invoice=service.create_invoice(BillingInvoiceCreate(patient_id=patient.id,discount_amount=D('.10'),discount_reason='Exact allocation',items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1) for _ in range(30)]),actor,{})
    assert all(item.net_amount>=0 for item in invoice.items)
    assert sum(item.net_amount for item in invoice.items)==D('.20')


def test_commission_reversal_after_approval_offsets_future_settlements(db):
    rules=FinancialRules(commission_enabled=True,commission_percentage=10,commission_approval_required=True,participants=[{'key':'agent','name':'Agent','kind':'agent','share':100}])
    actor,service,policies,invoice,_,_=setup_invoice(db,rules=rules,paid=1800)
    policies.settle(SettlementCreate(participant_key='agent',amount=180,approve_pending=True,request_key='approve-and-pay',reason='Approved commission payout'),actor)
    service.create_return(invoice.id,BillingReturnCreate(items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=2)],reason='Commission reversal after payout'),actor,{})
    assert sum(r.amount for r in policies.entries(actor) if r.participant_key=='agent')==-180
    with pytest.raises(AppException):
        policies.settle(SettlementCreate(participant_key='agent',amount=1,request_key='recovery-blocks-pay',reason='Must recover first'),actor)


def test_advance_collection_refunds_all_surplus_on_cancellation(db):
    from app.schemas.billing import BillingInvoiceCancelRequest
    actor,service,policies,invoice,_,_=setup_invoice(db,rules=FinancialRules(allow_advance_payments=True))
    invoice=service.create_payment(invoice.id,BillingPaymentCreate(amount=2000,advance=True,payment_method='cash',request_key='advance-collection'),actor,{})
    assert invoice.overpaid_amount==200 and invoice.due_amount==0
    invoice=service.cancel_invoice(invoice.id,BillingInvoiceCancelRequest(reason='Cancel including excess advance',request_key='cancel-with-advance'),actor,{})
    assert invoice.refunded_amount==2000 and invoice.paid_amount==0 and invoice.status=='void'


def test_package_policy_requires_whole_quantity(db):
    actor,service,policies,invoice,_,_=setup_invoice(db,rules=FinancialRules(package_cancellation='whole'))
    with pytest.raises(AppException,match='whole'):
        service.create_return(invoice.id,BillingReturnCreate(reason='Partial package denied',items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=1)]),actor,{})


def test_preview_uses_default_discount_and_enforces_frozen_catalog_limits(db):
    from app.schemas.billing import BillingInvoicePreviewRequest
    actor,service,policies,invoice,config,_=setup_invoice(db,rules=FinancialRules(default_discount_percentage=15),discount=0)
    preview=service.preview_invoice(BillingInvoicePreviewRequest(items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=2)]),actor)
    assert preview.total_amount==invoice.total_amount==1700
    from app.models.billing import BillingItemConfig
    db.get(BillingItemConfig,config['id']).max_discount_percentage=0;db.flush()
    with pytest.raises(AppException):
        service.preview_invoice(BillingInvoicePreviewRequest(items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=2)]),actor)


@pytest.mark.parametrize('model,changes',[(BillingPaymentCreate,{'amount':'0.001','payment_method':'cash'}),(BillingRefundCreate,{'amount':'0.001','reason':'Sub paisa rejected'}),(BillingInvoiceItemCreate,{'quantity':'1.001'}),(BillingInvoiceItemCreate,{'quantity':1,'discount_amount':'0.001'})])
def test_database_precision_boundary_is_enforced_before_posting(model,changes):
    with pytest.raises(ValidationError):model(**changes)


def test_explicit_override_role_can_exceed_policy_limit_but_not_prohibition():
    actor=NS(roles=[NS(code='DIRECTOR',is_active=True)])
    enforce_discount(line(),D(0),FinancialRules(max_percentage=10,override_roles=['DIRECTOR']),actor,True)
    with pytest.raises(AppException):enforce_discount(line(),D(0),FinancialRules(discounts_allowed=False,override_roles=['DIRECTOR']),actor,True)


def test_journal_numbers_keep_full_entropy_within_same_second(db,monkeypatch):
    from uuid import UUID
    import app.modules.accounting.service as accounting
    actor,_,_,invoice,_,_=setup_invoice(db,paid=100)
    fixed=datetime.now(UTC)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls,tz=None):return fixed
    identities=iter([UUID('abcd0000-0000-4000-8000-000000000001'),UUID('abcd0000-0000-4000-8000-000000000002')])
    monkeypatch.setattr(accounting,'datetime',FrozenDatetime)
    monkeypatch.setattr(accounting,'uuid4',lambda:next(identities))
    service=accounting.AccountingService(db)
    entries=[service._create_auto_entry(actor,'billing_test',str(index),fixed.date(),'Same-second collision regression',[('1001','Cash',D(1),D(0)),('4000','Revenue',D(0),D(1))]) for index in range(2)]
    db.flush()
    assert entries[0].journal_number!=entries[1].journal_number
    assert all(len(entry.journal_number)==50 for entry in entries)


def test_department_policy_follows_each_service_on_mixed_invoice(db):
    from app.modules.billing.operations import BillingOperations
    from app.schemas.billing import BillingTypeCreate
    actor,_,patient,_=seed(db);service=BillingServiceManager(db);policies=FinancialPolicies(db)
    categories=[BillingOperations(db).create_type(BillingTypeCreate(code=code,name=code,department=department),actor) for code,department in [('LAB','Pathology'),('CONS','Medicine')]]
    configs=[service.create_service(BillingServiceCreate(service_code=category.code,name=category.name,unit_price=1000,doctor_share_percentage=0,billing_type_id=category.id),actor,{}) for category in categories]
    for department,sharing in [('Pathology',{'hospital':100}),('Medicine',{'doctor':100})]:
        policies.create(PolicyCreate(scope='department',selector=department,effective_from=datetime.now(UTC)-timedelta(days=1),reason='Department discount sharing',rules=FinancialRules(doctor_key='doctor',doctor_revenue_percentage=70,discount_sharing=sharing)),actor)
    invoice=service.create_invoice(BillingInvoiceCreate(patient_id=patient.id,discount_percentage=10,discount_reason='Mixed departmental concession',items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1) for config in configs]),actor,{})
    by_department = {item.billing_department: item for item in invoice.items}
    assert by_department['Pathology'].financial_snapshot['rules']['discount_sharing']=={'hospital':'100'}
    assert by_department['Medicine'].financial_snapshot['rules']['discount_sharing']=={'doctor':'100'}
    assert sum(r.amount for r in policies.entries(actor))==1800


def test_same_doctor_receives_consultation_revenue_and_referral_commission():
    rules=FinancialRules(doctor_key='doctor',doctor_revenue_percentage=70,discount_sharing={'doctor':100},commission_enabled=True,commission_percentage=10,participants=[{'key':'doctor','name':'Consulting and referring doctor','kind':'doctor','share':100}])
    values=financial_values(line('800','100'),D(700),rules)
    assert values[('doctor','revenue')]==560 and values[('doctor','commission')]==70
    assert values[('doctor','discount')]==-100 and values[('hospital','revenue')]==170
    assert sum(values.values())==700


@pytest.mark.parametrize('field',['max_amount','hospital_fixed_deduction','commission_fixed','commission_limit'])
def test_policy_money_rejects_sub_paisa_configuration(field):
    with pytest.raises(ValidationError):FinancialRules(**{field:'0.005'})
