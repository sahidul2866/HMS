"""Prescription, template, payment and approved-catalog integration on isolated PostgreSQL."""
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from pydantic import ValidationError
from test_opd_workflow_integration import database,db,seed,visit  # noqa:F401
from app.core.exceptions import AppException
from app.models.encounter import OPDVisit,OPDVisitOrder
from app.models.prescription import PrescriptionRevision,ConfigurationProfileVersion,OPDExternalPayment
from app.models.billing import BillingPayment
from app.modules.opd.service import OPDService
from app.modules.opd.prescriptions import PrescriptionWorkflow,templates
from app.modules.configuration.service import ConfigurationService
from app.modules.configuration.prescription_presets import install_presets,PRESETS
from app.schemas.configuration import ConfigurationProfileCreate,ConfigurationProfileUpdate
from app.schemas.encounter import OPDVisitConsultationUpdate,OPDVisitOrderCreate
from app.schemas.prescription import FormField,validate_layout,PrescriptionAction,DirectConsultationPayment


def scenario(db):
    admin,doctors,patient,slot=seed(db)
    current=visit(db,admin,doctors[0],patient,slot)
    service=OPDService(db);service.update_status(current.id,'in_consultation',doctors[0],{})
    return admin,doctors,patient,current,service


def profile(db,actor,payload=None,**kwargs):
    return ConfigurationService(db).create_profile(ConfigurationProfileCreate(profile_type='prescription_layout',code='RX-'+uuid4().hex[:8],name='Test clinical template',payload=payload or {'paper_size':'A5','sections':['complaint','rx','investigation']},**kwargs),actor)


@pytest.mark.parametrize('state',['paid','doctor_direct','unpaid','free','waived','partial','follow_up','outstanding'])
def test_prescription_signing_independent_of_financial_state(db,state):
    admin,doctors,patient,current,service=scenario(db)
    if state=='follow_up':current.visit_type='follow_up'
    else:current.consultation_payment_status=state
    db.flush()
    signed=service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Recorded clinical assessment'),doctors[0],{})
    assert signed.prescription_status=='finalized'
    assert signed.consultation_payment_status==(state if state!='follow_up' else 'unpaid')
    assert db.scalar(select(func.count(BillingPayment.id)))==0
    assert signed.signed_prescription['final_diagnosis']=='Recorded clinical assessment'


@pytest.mark.parametrize('index',range(10))
def test_ten_editable_specialty_presets(db,index):
    admin,_,_,_=seed(db); ids=install_presets(db,admin)
    assert len(ids)==10 and install_presets(db,admin)==ids
    from app.models.configuration import ConfigurationProfile
    row=db.get(ConfigurationProfile,ids[index]);assert row.code=='rx-'+PRESETS[index][0]
    assert not row.payload.get('medicines')
    assert validate_layout(row.payload)==row.payload
    assert db.scalar(select(func.count(ConfigurationProfileVersion.id)))==10


@pytest.mark.parametrize('kind',['text','textarea','rich_text','number','date','select','searchable_select','checkbox','radio','medicine','investigation','diagnosis','vitals','notes','medicine_rows','investigation_rows','section','header','footer','table','columns'])
def test_safe_form_component_schema(kind):
    assert FormField(key='clinical_field',label='Clinical field / তথ্য',type=kind).type==kind


@pytest.mark.parametrize('payload',[{'fields':[{'key':'x','label':'x','type':'script'}]},{'fields':[{'key':'x','label':'<script>alert(1)</script>'}]},{'paper_size':'A5;url(javascript:bad)'},{'font_size':1000},{'fields':[{'key':'same','label':'a'},{'key':'same','label':'b'}]},{'fields':[{'key':'x','label':'x','show_when':{'missing':'a'}}]},{'fields':[{'key':'x','label':'x','show_when':{'y':'a'}},{'key':'y','label':'y','show_when':{'x':'b'}}]},{'fields':[{'key':'x','label':'x','min':10,'max':1}]},{'fields':[{'key':'x','label':'x','onclick':'evil()'}]}])
def test_invalid_or_executable_templates_rejected(payload):
    with pytest.raises((ValidationError,ValueError)):validate_layout(payload)


def test_versioned_template_edits_do_not_change_signed_prescriptions(db):
    admin,doctors,_,current,service=scenario(db)
    initial=profile(db,admin,{'paper_size':'A5','sections':['complaint','rx'],'fields':[{'key':'allergies','label':'Allergies','type':'textarea','required':True}]},scope='doctor',target_type='doctor',target_id=doctors[0].id)
    service.update_consultation(current.id,OPDVisitConsultationUpdate(prescription_template_id=initial.id,prescription_data={'allergies':'No known allergies documented'}),doctors[0],{})
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Initial assessment'),doctors[0],{})
    old=current.signed_prescription
    changed=ConfigurationService(db).update_profile(initial.id,ConfigurationProfileUpdate(name='Revised template',scope='doctor',target_type='doctor',target_id=doctors[0].id,payload={'paper_size':'A4','fields':[]}),admin)
    assert changed.version==2 and current.signed_prescription==old
    assert old['template_version']==1 and old['template_payload']['paper_size']=='A5'
    assert db.scalar(select(func.count(ConfigurationProfileVersion.id)))==2


def test_required_and_conditional_fields(db):
    admin,doctors,_,current,service=scenario(db)
    config=profile(db,admin,{'fields':[{'key':'pregnant','label':'Pregnant','type':'checkbox'},{'key':'gestation','label':'Gestation','type':'number','required':True,'min':1,'max':45,'show_when':{'pregnant':True}}]})
    service.update_consultation(current.id,OPDVisitConsultationUpdate(prescription_template_id=config.id,prescription_data={'pregnant':True}),doctors[0],{})
    with pytest.raises(AppException,match='required'):service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    service.update_consultation(current.id,OPDVisitConsultationUpdate(prescription_data={'pregnant':True,'gestation':20}),doctors[0],{})
    assert service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{}).prescription_status=='finalized'


def test_controlled_amendment_preserves_original_and_void_history(db):
    _,doctors,_,current,service=scenario(db)
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='First signed version'),doctors[0],{})
    first=current.signed_prescription
    with pytest.raises(AppException,match='amendment'):service.update_consultation(current.id,OPDVisitConsultationUpdate(final_diagnosis='Silent overwrite'),doctors[0],{})
    workflow=PrescriptionWorkflow(db)
    workflow.amend(current.id,PrescriptionAction(expected_version=current.clinical_version,reason='New clinical information'),doctors[0])
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Amended assessment'),doctors[0],{})
    rows=workflow.history(current.id,doctors[0]);assert len(rows)==2 and rows[0].snapshot==first
    assert rows[1].status=='amended' and rows[1].snapshot['final_diagnosis']=='Amended assessment'
    workflow.amend(current.id,PrescriptionAction(expected_version=current.clinical_version,reason='Entered for wrong encounter'),doctors[0],void=True)
    assert current.prescription_status=='voided' and len(workflow.history(current.id,doctors[0]))==3


def test_doctor_and_assistant_cannot_impersonate_another_signer(db):
    admin,doctors,_,current,service=scenario(db)
    with pytest.raises(AppException):service.get_visit(current.id,doctors[1])
    with pytest.raises(AppException):service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[1],{})
    with pytest.raises(AppException,match='assigned doctor'):service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),admin,{})
    assert db.scalar(select(func.count(PrescriptionRevision.id)))==0


def test_draft_autosave_version_conflict(db):
    _,doctors,_,current,service=scenario(db)
    version=current.clinical_version
    service.update_consultation(current.id,OPDVisitConsultationUpdate(expected_version=version,chief_complaint='Saved draft'),doctors[0],{})
    with pytest.raises(AppException,match='another session'):service.update_consultation(current.id,OPDVisitConsultationUpdate(expected_version=version,chief_complaint='Stale draft'),doctors[0],{})
    assert current.chief_complaint=='Saved draft'


def test_direct_doctor_payment_is_idempotent_and_never_hospital_cash(db):
    admin,doctors,_,current,service=scenario(db)
    ConfigurationService(db).create_profile(ConfigurationProfileCreate(profile_type='doctor_share',code='DR-SHARE',name='Doctor fee sharing',scope='doctor',target_id=doctors[0].id,payload={'method':'percentage','doctor_share_percentage':70}),admin)
    workflow=PrescriptionWorkflow(db)
    payload=DirectConsultationPayment(kind='doctor_direct',amount=500,reason='Doctor recorded direct receipt',request_key='direct-receipt-001')
    workflow.external_payment(current.id,payload,doctors[0]);workflow.external_payment(current.id,payload,doctors[0])
    rows=list(db.scalars(select(OPDExternalPayment)));assert len(rows)==1
    assert rows[0].settlement_snapshot['doctor_share']=='350.00' and rows[0].settlement_snapshot['hospital_share_due']=='150.00'
    assert rows[0].settlement_snapshot['verified'] is False
    assert db.scalar(select(func.count(BillingPayment.id)))==0
    assert service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{}).consultation_payment_status=='doctor_direct'


def test_investigation_duplicates_do_not_generate_orders_or_charges(db):
    _,doctors,_,current,service=scenario(db)
    payload=OPDVisitOrderCreate(order_type='investigation',service_area='laboratory',item_name='Synthetic CBC',request_key='lab-order-unique')
    service.create_order(current.id,payload,doctors[0],{});service.create_order(current.id,payload,doctors[0],{})
    service.create_order(current.id,OPDVisitOrderCreate(order_type='investigation',service_area='laboratory',item_name='synthetic cbc'),doctors[0],{})
    assert len(current.orders)==1
    from app.models.laboratory import LabOrder
    from app.models.billing import BillingInvoice
    assert db.scalar(select(func.count(LabOrder.id)))==1 and db.scalar(select(func.count(BillingInvoice.id)))==0


def test_long_bangla_prescription_and_cancelled_work_preserve_signed_snapshot(db):
    _,doctors,_,current,service=scenario(db)
    service.create_order(current.id,OPDVisitOrderCreate(order_type='investigation',service_area='laboratory',item_name='Synthetic investigation'),doctors[0],{})
    text='রোগীর পূর্বের ইতিহাস / patient history\n'*1000
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(history_of_present_illness=text,prescription_data={'weight_kg':12.5,'allergies':'অ্যালার্জি নথিভুক্ত'}),doctors[0],{})
    original=current.signed_prescription
    current.orders[0].status='cancelled';db.commit()
    assert current.signed_prescription==original and original['orders'][0]['status']=='pending'
    assert original['history_of_present_illness']==text


def test_signed_order_clinical_content_is_locked(db):
    _,doctors,_,current,service=scenario(db)
    service.create_order(current.id,OPDVisitOrderCreate(order_type='prescription',item_name='Synthetic medicine',instructions='Explicit doctor instruction'),doctors[0],{})
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    with pytest.raises(AppException):service.delete_order(current.id,current.orders[0].id,doctors[0],{})
    with pytest.raises(AppException):service.create_order(current.id,OPDVisitOrderCreate(order_type='prescription',item_name='Late item'),doctors[0],{})


@pytest.mark.parametrize('query',['Brand Test','Generic Test','B','alias spelling','500','Tablet','Test Manufacturer','ব্র্যান্ড'])
def test_approved_catalog_brand_generic_alias_strength_form_manufacturer_search(db,query):
    from app.models.pharmacy import PharmacyMedicine,PharmacyMedicineType,PharmacyGeneric,PharmacyCompany
    from app.modules.pharmacy.service import PharmacyService
    admin,_,_,_=seed(db)
    form=PharmacyMedicineType(name='Test Tablet');generic=PharmacyGeneric(name='Generic Test');company=PharmacyCompany(name='Test Manufacturer')
    db.add_all([form,generic,company]);db.flush()
    medicine=PharmacyMedicine(branch_id=admin.branch_id,name='Brand Test',generic_id=generic.id,medicine_type_id=form.id,company_id=company.id,strength='500 mg',dosage_form='Tablet',search_aliases=['alias spelling','ব্র্যান্ড'])
    db.add(medicine);db.flush()
    response=PharmacyService(db).list_medicines(admin,page=1,page_size=12,q=query)
    assert [row.id for row in response.items]==[medicine.id]


def test_hospital_consultation_payment_creates_real_receipt_and_keeps_clinical_state(db):
    from app.schemas.encounter import OPDVisitPaymentUpdate
    admin,doctors,_,current,service=scenario(db)
    before_status=current.status
    service.update_payment(current.id,OPDVisitPaymentUpdate(amount=500),admin,{})
    assert current.consultation_payment_status=='paid' and current.consultation_payment_source=='hospital'
    assert current.status==before_status and db.scalar(select(func.sum(BillingPayment.amount)))==500
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Paid consultation'),doctors[0],{})
    assert current.signed_prescription['final_diagnosis']=='Paid consultation'


def test_amending_completed_consultation_does_not_reopen_queue(db):
    _,doctors,_,current,service=scenario(db)
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    service.update_status(current.id,'completed',doctors[0],{})
    PrescriptionWorkflow(db).amend(current.id,PrescriptionAction(reason='Additional relevant history',expected_version=current.clinical_version),doctors[0])
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Updated after consultation completion'),doctors[0],{})
    assert current.status=='completed' and len(PrescriptionWorkflow(db).history(current.id,doctors[0]))==2


def test_template_scope_and_doctor_patient_history_isolation(db):
    from app.modules.patients.service import PatientsService
    from app.models.department import Department
    admin,doctors,patient,current,service=scenario(db)
    other=profile(db,admin,scope='doctor',target_type='doctor',target_id=doctors[1].id)
    assert other.id not in [row.id for row in templates(db,current)]
    service.update_consultation(current.id,OPDVisitConsultationUpdate(prescription_template_id=other.id),doctors[0],{})
    with pytest.raises(AppException,match='unavailable'):service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    assert PatientsService(db).get_patient_opd_visits(patient.id,doctors[1])==[]


def test_favorites_api_ownership_and_signed_api_history(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    admin,doctors,_,current,service=scenario(db)
    original=app.dependency_overrides.copy();acting=[doctors[0]]
    app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:acting[0]
    try:
        client=TestClient(app)
        response=client.post('/api/v1/opd/prescription-shortcuts',json={'kind':'advice','name':'Doctor-approved custom instructions','content':{'text':'Follow-up as documented by treating doctor'}})
        assert response.status_code==200,response.text
        identity=response.json()['id']
        assert len(client.get('/api/v1/opd/prescription-shortcuts').json())==1
        acting[0]=doctors[1]
        assert client.get('/api/v1/opd/prescription-shortcuts').json()==[]
        assert client.delete('/api/v1/opd/prescription-shortcuts/'+identity).status_code==404
        assert client.get(f'/api/v1/opd/visits/{current.id}/prescription-history').status_code==403
        acting[0]=doctors[0]
        response=client.post(f'/api/v1/opd/visits/{current.id}/finalize',json={'final_diagnosis':'API-signed assessment','expected_version':current.clinical_version})
        assert response.status_code==200,response.text
        repeated=client.post(f'/api/v1/opd/visits/{current.id}/finalize',json={'final_diagnosis':'Should not overwrite'})
        assert repeated.status_code==200
        assert len(client.get(f'/api/v1/opd/visits/{current.id}/prescription-history').json())==1
        assert current.final_diagnosis=='API-signed assessment'
    finally:app.dependency_overrides=original


def test_concurrent_draft_edits_have_one_winner(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from app.models.base import Base
    from app.models.user import User
    schema='rx_race_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema});Base.metadata.create_all(engine)
    try:
        with Session(engine,expire_on_commit=False) as session:
            _,doctors,_,current,service=scenario(session);identity=current.id;doctor_id=doctors[0].id;version=current.clinical_version
        barrier=Barrier(2)
        def save(index):
            with Session(engine,expire_on_commit=False) as session:
                doctor=session.get(User,doctor_id);barrier.wait(timeout=10)
                try:OPDService(session).update_consultation(identity,OPDVisitConsultationUpdate(expected_version=version,chief_complaint='Concurrent '+str(index)),doctor,{});return 'saved'
                except AppException:session.rollback();return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(save,range(2)))
        assert sorted(result)==['conflict','saved']
        with Session(engine) as session:assert session.get(OPDVisit,identity).clinical_version==version+1
    finally:
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_prescription_migration_preserves_legacy_records_and_immutable_versions(database):
    import importlib.util
    from pathlib import Path
    from sqlalchemy import text,inspect
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import DBAPIError
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.models.base import Base
    schema='rx_migration_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema})
    new_tables={'prescription_events','prescription_revisions','configuration_profile_versions','opd_external_payments','prescription_shortcuts'}
    Base.metadata.create_all(engine,tables=[table for table in Base.metadata.sorted_tables if table.name not in new_tables])
    try:
        with Session(engine,expire_on_commit=False) as session:
            admin,doctors,patient,slot=seed(session);current=OPDVisit(branch_id=admin.branch_id,patient_id=patient.id,consulting_doctor_user_id=doctors[0].id,consulting_doctor_name=doctors[0].full_name,department_name='Medicine',visit_number='LEGACY-'+uuid4().hex,visit_date=slot.date(),registered_by_user_id=admin.id,status='prescribed',final_diagnosis='Legacy signed clinical data');session.add(current);session.commit();identity=current.id
        spec=importlib.util.spec_from_file_location('rx_migration',Path(__file__).parents[1]/'alembic/versions/20261119_0077_prescription_lifecycle.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with engine.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO {schema}'))
            for table,columns in {'opd_visits':['prescription_data','prescription_template_id','clinical_version','prescription_status','consultation_payment_source'],'opd_visit_orders':['prescription_detail','request_key','version'],'configuration_profiles':['version'],'pharmacy_medicines':['search_aliases'],'users':['opd_bmdc_registration','opd_signature_image']}.items():
                for column in columns:conn.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
            with Operations.context(MigrationContext.configure(conn)):module.upgrade()
            stored=conn.execute(text('SELECT snapshot,signed_at FROM prescription_revisions WHERE visit_id=:id'),{'id':identity}).one()
            assert stored.snapshot['legacy_import'] is True and stored.signed_at is None
            assert stored.snapshot['final_diagnosis']=='Legacy signed clinical data'
            assert 'hashed_password' not in str(stored.snapshot)
            savepoint=conn.begin_nested()
            with pytest.raises(DBAPIError,match='append-only'):conn.execute(text("UPDATE prescription_revisions SET status='voided'"))
            savepoint.rollback()
            with Operations.context(MigrationContext.configure(conn)):module.downgrade()
            assert 'prescription_revisions' not in inspect(conn).get_table_names(schema=schema)
            assert conn.scalar(text('SELECT final_diagnosis FROM opd_visits WHERE id=:id'),{'id':identity})=='Legacy signed clinical data'
    finally:
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_follow_up_is_new_record_with_prior_signed_history(db):
    admin,doctors,patient,current,service=scenario(db)
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Original diagnosis'),doctors[0],{})
    from app.schemas.encounter import OPDVisitCreate
    follow=service.create_visit(OPDVisitCreate(patient_id=patient.id,doctor_user_id=doctors[0].id,consulting_doctor_name=doctors[0].full_name,department_name='Medicine',visit_date=current.visit_date,visit_type='follow_up'),admin,{})
    assert follow.id!=current.id and follow.visit_type=='follow_up'
    assert current.signed_prescription['final_diagnosis']=='Original diagnosis'
    assert follow.prescription_status=='draft'


def test_direct_receipt_cannot_be_duplicated_or_exceed_consultation_balance(db):
    _,doctors,_,current,_=scenario(db);workflow=PrescriptionWorkflow(db)
    workflow.external_payment(current.id,DirectConsultationPayment(kind='doctor_direct',amount=300,reason='First part direct receipt',request_key='partial-direct-001'),doctors[0])
    with pytest.raises(AppException):workflow.external_payment(current.id,DirectConsultationPayment(kind='doctor_direct',amount=201,reason='Excess direct collection',request_key='partial-direct-002'),doctors[0])
    assert db.scalar(select(func.sum(OPDExternalPayment.amount)))==300


def test_billing_refund_and_configuration_changes_do_not_delete_prescription(db):
    from app.schemas.encounter import OPDVisitPaymentUpdate
    from app.schemas.billing import BillingRefundCreate
    from app.modules.billing.service import BillingServiceManager
    from app.models.billing import BillingInvoice
    admin,doctors,_,current,service=scenario(db)
    service.update_payment(current.id,OPDVisitPaymentUpdate(amount=500),admin,{})
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(final_diagnosis='Clinical record survives financial reversal'),doctors[0],{})
    original=current.signed_prescription
    invoice=db.scalar(select(BillingInvoice).where(BillingInvoice.source_opd_visit_id==current.id))
    BillingServiceManager(db).create_refund(invoice.id,BillingRefundCreate(amount=500,reason='Audited financial refund'),admin,{})
    assert current.signed_prescription==original and current.status=='prescribed'


def test_prescribing_catalog_performance_with_ten_thousand_synthetic_entries(db):
    import json,time,statistics
    from pathlib import Path
    from sqlalchemy import insert
    from app.models.pharmacy import PharmacyMedicine,PharmacyMedicineType,PharmacyGeneric,PharmacyCompany
    from app.modules.pharmacy.service import PharmacyService
    admin,_,_,_=seed(db)
    form=PharmacyMedicineType(name='Synthetic form');generic=PharmacyGeneric(name='Synthetic generic');company=PharmacyCompany(name='Synthetic manufacturer')
    db.add_all([form,generic,company]);db.flush()
    db.execute(insert(PharmacyMedicine),[{'id':uuid4(),'branch_id':admin.branch_id,'medicine_type_id':form.id,'generic_id':generic.id,'company_id':company.id,'name':f'Synthetic Brand {index:05d}','strength':'TEST ONLY','dosage_form':'Synthetic form','search_aliases':['synthetic alias']} for index in range(10000)])
    timings=[]
    for query in ['Synthetic Brand 09999','Synthetic generic','synthetic alias','S']:
        start=time.perf_counter();result=PharmacyService(db).list_medicines(admin,page=1,page_size=12,q=query);timings.append(round((time.perf_counter()-start)*1000,2))
        assert result.items and len(result.items)<=12
    report={'catalog_size':10000,'queries':4,'timings_ms':timings,'median_ms':statistics.median(timings),'max_ms':max(timings),'scope':'Local PostgreSQL service search including count and page hydration; synthetic entries; not production latency'}
    Path('/tmp/hms-prescription-search-performance.json').write_text(json.dumps(report,indent=2))
    assert max(timings)<2000,report


def test_configured_canonical_field_updates_shared_printed_clinical_data(db):
    _,doctors,_,current,service=scenario(db)
    service.update_consultation(current.id,OPDVisitConsultationUpdate(prescription_data={'chief_complaint':'Configured complaint field','follow_up_date':'2026-12-01'}),doctors[0],{})
    assert current.chief_complaint=='Configured complaint field' and current.follow_up_date.isoformat()=='2026-12-01'
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    assert current.signed_prescription['chief_complaint']=='Configured complaint field'


def test_reception_edit_endpoint_cannot_change_signed_clinical_identity(db):
    from app.schemas.encounter import OPDVisitUpdate
    admin,doctors,_,current,service=scenario(db)
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(chief_complaint='Preserve original complaint'),doctors[0],{})
    with pytest.raises(AppException,match='controlled'):
        service.update_visit(current.id,OPDVisitUpdate(visit_date=current.visit_date,slot_start_at=current.slot_start_at,department_name=current.department_name,doctor_user_id=doctors[1].id,consulting_doctor_name=doctors[1].full_name,consultation_fee=500,chief_complaint='Overwritten'),admin,{})


def test_voided_prescription_cannot_be_dispensed(db):
    from app.modules.pharmacy.service import PharmacyService
    from app.schemas.pharmacy import PharmacyDispenseCreate
    admin,doctors,_,current,service=scenario(db)
    service.create_order(current.id,OPDVisitOrderCreate(order_type='prescription',item_name='Synthetic medication',instructions='Explicit instructions'),doctors[0],{})
    order=current.orders[0]
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    PrescriptionWorkflow(db).amend(current.id,PrescriptionAction(reason='Entered in error',expected_version=current.clinical_version),doctors[0],void=True)
    with pytest.raises(AppException,match='cancelled'):PharmacyService(db).dispense(PharmacyDispenseCreate(source_visit_order_id=order.id,medicine_name=order.item_name,quantity=1,unit_price=0),admin,{})


def test_amendment_can_withdraw_completed_item_without_reversing_completed_care(db):
    _,doctors,_,current,service=scenario(db)
    service.create_order(current.id,OPDVisitOrderCreate(order_type='prescription',item_name='Synthetic old course'),doctors[0],{})
    order=current.orders[0]
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    original=current.signed_prescription
    order.status='completed';db.commit()
    PrescriptionWorkflow(db).amend(current.id,PrescriptionAction(reason='Clinical course superseded',expected_version=current.clinical_version),doctors[0])
    service.delete_order(current.id,order.id,doctors[0],{})
    service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    assert order.status=='completed' and current.signed_prescription['orders']==[]
    assert PrescriptionWorkflow(db).history(current.id,doctors[0])[0].snapshot==original


def test_draft_and_sign_audit_keeps_before_after_values(db):
    from app.models.prescription import PrescriptionEvent
    _,doctors,_,current,service=scenario(db)
    service.update_consultation(current.id,OPDVisitConsultationUpdate(chief_complaint='First content'),doctors[0],{})
    service.update_consultation(current.id,OPDVisitConsultationUpdate(chief_complaint='Revised content'),doctors[0],{})
    rows=list(db.scalars(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==current.id).order_by(PrescriptionEvent.created_at)))
    assert rows[0].kind=='created'
    assert rows[-1].detail['before']['chief_complaint']=='First content'
    assert rows[-1].detail['after']['chief_complaint']=='Revised content'


def test_external_finance_review_is_authorized_immutable_and_cash_free(db):
    from app.schemas.prescription import ExternalPaymentReview
    from app.models.prescription import PrescriptionEvent
    admin,doctors,patient,current,service=scenario(db)
    ConfigurationService(db).create_profile(ConfigurationProfileCreate(profile_type='doctor_share',code='DIRECT-SHARE',name='Approved share',target_type='doctor',target_id=doctors[0].id,payload={'doctor_share_percentage':70}),admin)
    workflow=PrescriptionWorkflow(db)
    workflow.external_payment(current.id,DirectConsultationPayment(kind='doctor_direct',amount=100,reason='Doctor receipt',request_key='direct-test-review'),doctors[0])
    claim=db.scalar(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==current.id))
    payload=ExternalPaymentReview(decision='verified',evidence='Finance checked receipt REF-001',request_key='verify-direct-test')
    with pytest.raises(AppException):workflow.review_external_payment(current.id,claim.id,payload,doctors[0])
    result=workflow.review_external_payment(current.id,claim.id,payload,admin)
    assert result.detail['decision']=='verified'
    assert result.detail['settlement_snapshot']['hospital_share_due']=='30.00'
    assert workflow.review_external_payment(current.id,claim.id,payload,admin).id==result.id
    with pytest.raises(AppException):workflow.review_external_payment(current.id,claim.id,payload.model_copy(update={'request_key':'another-review-key','decision':'rejected'}),admin)
    assert db.scalar(select(func.count(BillingPayment.id)))==0
    assert claim.settlement_snapshot['verified'] is False
    assert db.scalar(select(func.count(PrescriptionEvent.id)).where(PrescriptionEvent.kind=='external_payment_review'))==1


def test_template_logo_rejects_external_and_executable_images():
    for logo in ['https://remote.example/logo.png','data:image/svg+xml;base64,PHN2Zz4=','data:image/png;base64,PHNjcmlwdD4=']:
        with pytest.raises(ValueError):validate_layout({'hospital_logo':logo})
    import base64
    image='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
    assert validate_layout({'hospital_name':'Clinic / ক্লিনিক','hospital_logo':image})['hospital_logo']==image


def test_required_repeating_medicines_uses_real_orders_not_unlinked_form_rows(db):
    admin,doctors,patient,current,service=scenario(db)
    template=profile(db,admin,{'fields':[{'key':'meds','label':'Confirmed medicines','type':'medicine_rows','required':True}]})
    service.update_consultation(current.id,OPDVisitConsultationUpdate(prescription_template_id=template.id,prescription_data={'meds':[{'name':'Unlinked form text'}]}),doctors[0],{})
    with pytest.raises(AppException,match='confirmed clinical order'):service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    service.create_order(current.id,OPDVisitOrderCreate(order_type='prescription',item_name='Explicit clinician entry',quantity=1),doctors[0],{})
    signed=service.finalize_prescription(current.id,OPDVisitConsultationUpdate(),doctors[0],{})
    assert len(signed.signed_prescription['orders'])==1


def test_stale_order_update_does_not_replace_new_dosage(db):
    from app.schemas.encounter import OPDVisitOrderUpdate
    admin,doctors,patient,current,service=scenario(db)
    service.create_order(current.id,OPDVisitOrderCreate(order_type='prescription',item_name='Explicit clinician entry',instructions='First recorded instructions',quantity=1),doctors[0],{})
    order=current.orders[0];version=order.version
    service.update_order(current.id,order.id,OPDVisitOrderUpdate(expected_version=version,instructions='New clinician instructions'),doctors[0],{})
    with pytest.raises(AppException,match='another session'):service.update_order(current.id,order.id,OPDVisitOrderUpdate(expected_version=version,instructions='Stale instructions'),doctors[0],{})
    assert order.instructions=='New clinician instructions'


def test_actual_direct_remittance_links_existing_cash_once_and_reversal_reopens_balance(db):
    from app.schemas.prescription import ExternalPaymentReview,ExternalRemittanceLink
    from app.schemas.accounting import JournalEntryCreate,JournalEntryLineCreate
    from app.modules.accounting.service import AccountingService
    from app.models.prescription import PrescriptionEvent
    from app.models.accounting import Account,JournalEntry
    from app.modules.opd.router import external_payment_records
    admin,doctors,_,current,service=scenario(db)
    ConfigurationService(db).create_profile(ConfigurationProfileCreate(profile_type='doctor_share',code='REMIT-SHARE',name='Approved share',target_type='doctor',target_id=doctors[0].id,payload={'doctor_share_percentage':70}),admin)
    workflow=PrescriptionWorkflow(db)
    workflow.external_payment(current.id,DirectConsultationPayment(kind='doctor_direct',amount=500,reason='Doctor receipt',request_key='remit-claim-key'),doctors[0])
    claim=db.scalar(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==current.id))
    accounting=AccountingService(db)
    receipt=accounting.create_journal_entry(JournalEntryCreate(journal_date=current.visit_date,source_module='opd_external_remittance',source_reference=str(claim.id),narration='Actual hospital share remittance',status='posted',lines=[JournalEntryLineCreate(account_code='1001',account_name='Cash / Bank',debit_amount=150),JournalEntryLineCreate(account_code='1160',account_name='Doctor remittance clearing',credit_amount=150)]),admin,{})
    payload=ExternalRemittanceLink(journal_id=receipt.id,amount=150,evidence='Actual receipt checked by finance',request_key='linked-remit-key')
    with pytest.raises(AppException,match='Verify'):workflow.link_external_remittance(current.id,claim.id,payload,admin)
    workflow.review_external_payment(current.id,claim.id,ExternalPaymentReview(decision='verified',evidence='Finance verified doctor receipt',request_key='remit-verify-key'),admin)
    with pytest.raises(AppException):workflow.link_external_remittance(current.id,claim.id,payload,doctors[0])
    result=workflow.link_external_remittance(current.id,claim.id,payload,admin)
    assert result.detail['remaining_hospital_share']=='0.00'
    assert workflow.link_external_remittance(current.id,claim.id,payload,admin).id==result.id
    with pytest.raises(AppException,match='exceeds'):workflow.link_external_remittance(current.id,claim.id,payload.model_copy(update={'amount':Decimal(1),'request_key':'another-remit-key'}),admin)
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001',Account.branch_id==admin.branch_id))==150
    assert db.scalar(select(func.count(JournalEntry.id)))==1
    assert db.scalar(select(func.count(BillingPayment.id)))==0
    records=external_payment_records(current.id,admin,db);assert records[0]['hospital_share_remaining']=='0.00'
    accounting.reverse_journal_entry(receipt,admin,{});db.commit()
    assert external_payment_records(current.id,admin,db)[0]['hospital_share_remaining']=='150.00'
    assert db.scalar(select(func.count(PrescriptionEvent.id)).where(PrescriptionEvent.kind=='external_remittance_link'))==1


@pytest.mark.parametrize('decision',[None,'verified','rejected'])
def test_hospital_cannot_collect_consultation_already_covered_by_external_claim(db,decision):
    from app.schemas.encounter import OPDVisitPaymentUpdate
    from app.schemas.prescription import ExternalPaymentReview
    admin,doctors,_,current,service=scenario(db)
    ConfigurationService(db).create_profile(ConfigurationProfileCreate(profile_type='doctor_share',code='CASH-GUARD',name='Approved share',target_type='doctor',target_id=doctors[0].id,payload={'doctor_share_percentage':70}),admin)
    workflow=PrescriptionWorkflow(db)
    workflow.external_payment(current.id,DirectConsultationPayment(kind='doctor_direct',amount=500,reason='Doctor receipt',request_key='cash-guard-claim'),doctors[0])
    claim=db.scalar(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==current.id))
    if decision:workflow.review_external_payment(current.id,claim.id,ExternalPaymentReview(decision=decision,evidence='Finance evidence checked',request_key='cash-guard-review'),admin)
    if decision=='rejected':
        service.update_payment(current.id,OPDVisitPaymentUpdate(amount=500),admin,{})
        assert db.scalar(select(func.sum(BillingPayment.amount)))==500
    else:
        with pytest.raises(AppException,match='Doctor-direct receipt'):service.update_payment(current.id,OPDVisitPaymentUpdate(amount=500),admin,{})
        assert db.scalar(select(func.count(BillingPayment.id)))==0
