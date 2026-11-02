from datetime import UTC, datetime, timedelta, date
from uuid import uuid4
import pytest
from sqlalchemy import select
from test_opd_workflow_integration import database, db, seed
from app.core.exceptions import AppException
from app.models.branch import Branch
from app.models.blood_bank import BloodUnit, BloodCrossmatch, BloodIssue, BloodRequest
from app.modules.blood_bank.service import BloodBankService
from app.schemas.blood_bank import BloodDonorCreate, DonorScreeningCreate, BloodCollectionCreate, BloodTestResultCreate, ComponentPrepareCreate, BloodRequestCreate, CrossmatchCreate, BloodIssueCreate, TransfusionCreate, BloodReturnCreate
from app.modules.ot.service import OTService
from app.schemas.ot import OTRoomCreate, OTBookingCreate, SurgeryScheduleCreate, PreOpChecklistUpdate, AnesthesiaRecordUpdate, SurgeryNoteUpdate, OTBillingItemCreate


def unit(db, actor):
    service=BloodBankService(db,actor)
    donor=service.create_donor(BloodDonorCreate(name='Synthetic donor '+uuid4().hex[:8],age=30,blood_group='A+',gender='male'),actor,{})
    service.screen_donor(DonorScreeningCreate(donor_id=donor.id,eligibility_result='eligible'),actor,{})
    collection=service.collect_blood(BloodCollectionCreate(donor_id=donor.id,blood_group='A+',collection_volume_ml=450,expiry_date=date.today()+timedelta(days=20)),actor,{})
    row=db.scalar(select(BloodUnit).where(BloodUnit.collection_id==collection.id))
    service.update_test(BloodTestResultCreate(unit_id=row.id,test_name='Synthetic screen',status='completed',result='negative',verified=True),actor,{})
    return row


def request(db, actor, patient):
    return BloodBankService(db,actor).create_request(BloodRequestCreate(patient_id=patient.id,blood_group='A+',component_type='Whole Blood',quantity_units=1),actor,{})


def issued(db, actor, patient):
    u=unit(db,actor);r=request(db,actor,patient);svc=BloodBankService(db,actor)
    c=svc.crossmatch(CrossmatchCreate(request_id=r.id,unit_id=u.id,patient_blood_group='A+',result='compatible',compatibility_status='compatible'),actor,{})
    issue=svc.issue(BloodIssueCreate(request_id=r.id,unit_id=u.id,crossmatch_id=c.id,received_by='Synthetic staff'),actor,{})
    return u,r,issue


def test_blood_crossmatch_cannot_be_substituted_for_another_request(db):
    actor,_,patient,_=seed(db);svc=BloodBankService(db,actor);u=unit(db,actor);r=request(db,actor,patient);other=request(db,actor,patient)
    c=svc.crossmatch(CrossmatchCreate(request_id=r.id,unit_id=u.id,patient_blood_group='A+',result='compatible',compatibility_status='compatible'),actor,{})
    with pytest.raises(AppException):svc.issue(BloodIssueCreate(request_id=other.id,unit_id=u.id,crossmatch_id=c.id),actor,{})
    assert u.status=='crossmatched'


def test_transfused_blood_cannot_be_returned_or_restarted(db):
    actor,_,patient,_=seed(db);u,r,i=issued(db,actor,patient);svc=BloodBankService(db,actor)
    svc.transfusion(TransfusionCreate(issue_id=i.id,status='started'),actor,{})
    with pytest.raises(AppException):svc.return_unit(BloodReturnCreate(issue_id=i.id,decision='accept',reason='Not unused'),actor,{})
    t=svc.transfusion(TransfusionCreate(issue_id=i.id,status='completed'),actor,{})
    assert t.completed_at and t.completed_by==actor.id and u.status=='transfused'
    with pytest.raises(AppException):svc.transfusion(TransfusionCreate(issue_id=i.id,status='started'),actor,{})


def test_unused_blood_return_once_then_new_request_reissue(db):
    actor,_,patient,_=seed(db);u,r,i=issued(db,actor,patient);svc=BloodBankService(db,actor)
    payload=BloodReturnCreate(issue_id=i.id,decision='accept',reason='Unused sealed unit inspected',condition_on_return='Seal intact, inspected',minutes_outside_bank=2)
    svc.return_unit(payload,actor,{})
    with pytest.raises(AppException):svc.return_unit(payload,actor,{})
    r2=request(db,actor,patient);c=svc.crossmatch(CrossmatchCreate(request_id=r2.id,unit_id=u.id,patient_blood_group='A+',result='compatible',compatibility_status='compatible'),actor,{})
    i2=svc.issue(BloodIssueCreate(request_id=r2.id,unit_id=u.id,crossmatch_id=c.id),actor,{})
    assert i2.id!=i.id and u.status=='issued'


def test_component_volume_conserved_and_parent_not_issuable(db):
    actor,_,patient,_=seed(db);u=unit(db,actor);svc=BloodBankService(db,actor)
    child=svc.prepare_component(ComponentPrepareCreate(source_unit_id=u.id,component_type='Packed Red Blood Cells',volume_ml=250,expiry_date=date.today()+timedelta(days=10)),actor,{})
    assert child.volume_ml==250 and u.status=='processed'
    with pytest.raises(AppException):svc.prepare_component(ComponentPrepareCreate(source_unit_id=u.id,component_type='Plasma',volume_ml=300,expiry_date=date.today()+timedelta(days=10)),actor,{})
    with pytest.raises(AppException):svc.crossmatch(CrossmatchCreate(request_id=request(db,actor,patient).id,unit_id=u.id,patient_blood_group='A+',result='compatible',compatibility_status='compatible'),actor,{})


def test_reactive_result_not_hidden_by_later_negative_test(db):
    actor,_,_,_=seed(db);u=unit(db,actor);svc=BloodBankService(db,actor)
    svc.update_test(BloodTestResultCreate(unit_id=u.id,test_name='Reactive synthetic screen',status='completed',result='positive',verified=True),actor,{})
    svc.update_test(BloodTestResultCreate(unit_id=u.id,test_name='Different synthetic screen',status='completed',result='negative',verified=True),actor,{})
    assert u.status=='quarantined' and u.testing_status=='reactive'


def test_blood_reads_and_changes_are_branch_scoped(db):
    actor,_,patient,_=seed(db);u=unit(db,actor);r=request(db,actor,patient)
    other=Branch(code='BLOOD-'+uuid4().hex[:8],name='Other branch');db.add(other);db.flush();actor.branch_id=other.id;db.commit();svc=BloodBankService(db,actor)
    assert svc.list_units(None,None,None,None,1,20)['items']==[]
    assert svc.list_requests(None,None,1,20)['items']==[]
    assert svc.report('stock',None,None).rows==[]
    with pytest.raises(AppException):svc.update_test(BloodTestResultCreate(unit_id=u.id,test_name='Wrong branch',status='completed'),actor,{})


def ot_case(db):
    actor,_,patient,_=seed(db);svc=OTService(db);start=datetime.now(UTC)+timedelta(days=1)
    room=svc.create_room(OTRoomCreate(room_number='OT-'+uuid4().hex[:8],name='Synthetic OT'),actor)
    booking=svc.create_booking(OTBookingCreate(patient_id=patient.id,procedure_name='Synthetic surgery',preferred_start_at=start),actor)
    schedule=svc.create_schedule(SurgeryScheduleCreate(booking_id=booking.id,room_id=room.id,scheduled_start_at=start,scheduled_end_at=start+timedelta(hours=1)),actor)
    return actor,svc,schedule


def test_ot_requires_readiness_and_sequence_before_completion(db):
    actor,svc,s=ot_case(db)
    with pytest.raises(AppException):svc.update_status(s.id,'in_progress',actor)
    svc.upsert_pre_op(s.id,PreOpChecklistUpdate(ready_for_ot=True,consent_signed=True),actor)
    assert s.status=='scheduled'
    svc.upsert_anesthesia(s.id,AnesthesiaRecordUpdate(clearance_status='cleared',pre_assessment='Synthetic assessment complete'),actor)
    svc.update_status(s.id,'in_progress',actor)
    with pytest.raises(AppException):svc.update_status(s.id,'completed',actor)
    svc.upsert_surgery_note(s.id,SurgeryNoteUpdate(surgeon_notes='Synthetic operative findings'),actor)
    svc.update_status(s.id,'completed',actor)
    assert s.room.status=='cleaning'
    with pytest.raises(AppException):svc.update_status(s.id,'in_progress',actor)
    with pytest.raises(AppException):svc.upsert_pre_op(s.id,PreOpChecklistUpdate(ready_for_ot=True),actor)


def test_ot_charge_creates_one_real_cashier_invoice(db):
    actor,svc,s=ot_case(db)
    charge=svc.add_billing_item(OTBillingItemCreate(schedule_id=s.id,charge_type='procedure',description='Synthetic case charge',amount=500),actor)
    first=svc.post_charge_invoice(charge.id,actor,{})
    assert first==svc.post_charge_invoice(charge.id,actor,{})
    from app.models.billing import BillingInvoice
    invoice=db.get(BillingInvoice,charge.billing_invoice_id)
    assert invoice.patient_id==s.booking.patient_id and invoice.total_amount==500
    with pytest.raises(AppException):svc.add_billing_item(OTBillingItemCreate(schedule_id=s.id,charge_type='procedure',description='Cannot claim paid without receipt',amount=20,payment_status='paid'),actor)


@pytest.mark.parametrize('kind', ['lab','radiology'])
def test_linked_diagnostics_appear_once_and_release_only_verified_findings(db,kind):
    from app.models.encounter import OPDVisit,OPDVisitOrder
    from app.models.laboratory import LabOrder,LabOrderItem
    from app.models.radiology import RadiologyOrder
    from app.modules.laboratory.service import LaboratoryService
    from app.modules.radiology.service import RadiologyService
    from app.modules.patient_portal.service import PatientPortalService
    from app.schemas.encounter import ClinicalInvestigationResultUpdate
    actor,_,patient,_=seed(db)
    visit=OPDVisit(branch_id=actor.branch_id,patient_id=patient.id,visit_number='SYNC-'+uuid4().hex[:10],visit_date=date.today(),department_name='Synthetic',consulting_doctor_name='Synthetic doctor',registered_by_user_id=actor.id)
    db.add(visit);db.flush()
    domain=(LabOrder if kind=='lab' else RadiologyOrder)(branch_id=actor.branch_id,patient_id=patient.id,visit_id=visit.id,order_number='LINK-'+uuid4().hex[:10],status='pending')
    if kind=='radiology':domain.study_description='Synthetic study'
    db.add(domain);db.flush()
    if kind=='lab':db.add(LabOrderItem(order_id=domain.id,test_name='Synthetic test',quantity=1))
    legacy=OPDVisitOrder(visit_id=visit.id,order_type='investigation',service_area='laboratory' if kind=='lab' else 'radiology',item_name='Synthetic test',quantity=1,status='pending',**{('lab_order_id' if kind=='lab' else 'radiology_order_id'):domain.id})
    db.add(legacy);db.commit()
    service=(LaboratoryService if kind=='lab' else RadiologyService)(db)
    assert len([r for r in service.list_worklist(actor) if r.patient_id==patient.id])==1
    service.update_result(domain.id,ClinicalInvestigationResultUpdate(status='completed',result_text='Working findings not released'),actor,{})
    assert legacy.status=='completed' and legacy.result_text=='Working findings not released'
    actor.patient_id=patient.id
    overview=PatientPortalService(db).get_overview(actor)
    assert overview.patient.opd_visits[0].orders[0].result_text is None
    service.update_result(domain.id,ClinicalInvestigationResultUpdate(status='verified'),actor,{})
    released=PatientPortalService(db).get_overview(actor)
    assert released.patient.opd_visits[0].orders[0].status=='verified'
    assert released.patient.opd_visits[0].orders[0].result_text=='Working findings not released'


def test_ot_room_turnover_requires_active_surgery_to_finish(db):
    actor,svc,s=ot_case(db)
    svc.upsert_pre_op(s.id,PreOpChecklistUpdate(ready_for_ot=True,consent_signed=True),actor)
    svc.upsert_anesthesia(s.id,AnesthesiaRecordUpdate(clearance_status='cleared'),actor)
    svc.update_status(s.id,'in_progress',actor)
    with pytest.raises(AppException):svc.update_room_status(s.room_id,'available','Cannot release occupied theatre',actor)
    svc.upsert_surgery_note(s.id,SurgeryNoteUpdate(surgeon_notes='Synthetic completed operation'),actor)
    svc.update_status(s.id,'completed',actor)
    svc.update_room_status(s.room_id,'available','Cleaning completed and inspected',actor)
    assert s.room.status=='available'


def test_blood_reports_use_actual_transfusion_and_date_filters(db):
    actor,_,patient,_=seed(db);u,r,i=issued(db,actor,patient);svc=BloodBankService(db,actor)
    assert svc.report('transfusion',None,None).rows==[]
    svc.transfusion(TransfusionCreate(issue_id=i.id,status='completed'),actor,{})
    report=svc.report('transfusion',date.today()-timedelta(days=1),date.today()+timedelta(days=1))
    assert len(report.rows)==1 and report.rows[0]['unit_number']==u.unit_number and report.rows[0]['status']=='completed'
    assert svc.report('transfusion',date.today()-timedelta(days=10),date.today()-timedelta(days=5)).rows==[]
    with pytest.raises(AppException):svc.report('transfusion',date.today()+timedelta(days=1),date.today())


from contextlib import contextmanager


@contextmanager
def isolated_race_database(parent):
    from sqlalchemy import text
    from app.models.base import Base
    schema='specialist_race_'+uuid4().hex
    with parent.begin() as connection:connection.execute(text('CREATE SCHEMA '+schema))
    isolated=parent.execution_options(schema_translate_map={None:schema})
    try:
        Base.metadata.create_all(isolated)
        yield isolated
    finally:
        with parent.begin() as connection:connection.execute(text('DROP SCHEMA '+schema+' CASCADE'))


def test_concurrent_blood_issue_posts_only_once(database):
    with isolated_race_database(database) as database:
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from sqlalchemy.orm import Session
        from app.models.user import User
        with Session(database,expire_on_commit=False,autoflush=False) as session:
            actor,_,patient,_=seed(session);session.commit()
            u=unit(session,actor);r=request(session,actor,patient);svc=BloodBankService(session,actor)
            c=svc.crossmatch(CrossmatchCreate(request_id=r.id,unit_id=u.id,patient_blood_group='A+',result='compatible',compatibility_status='compatible'),actor,{})
            identifiers=(actor.id,u.id,r.id,c.id)
        ready=Barrier(2)
        def attempt():
            with Session(database,expire_on_commit=False,autoflush=False) as session:
                actor=session.get(User,identifiers[0]);ready.wait(timeout=10)
                try:
                    BloodBankService(session,actor).issue(BloodIssueCreate(request_id=identifiers[2],unit_id=identifiers[1],crossmatch_id=identifiers[3]),actor,{})
                    return 200
                except AppException as error:
                    session.rollback();return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
        assert sorted(results)==[200,409]
        with Session(database) as session:
            assert len(list(session.scalars(select(BloodIssue).where(BloodIssue.unit_id==identifiers[1]))))==1


def test_ot_calendar_uses_dhaka_day_across_utc_midnight(db):
    actor,_,patient,_=seed(db);svc=OTService(db)
    start=datetime(2026,11,1,22,0,tzinfo=UTC)
    room=svc.create_room(OTRoomCreate(room_number='TZ-'+uuid4().hex[:8],name='Timezone test theatre'),actor)
    booking=svc.create_booking(OTBookingCreate(patient_id=patient.id,procedure_name='Dhaka night case',preferred_start_at=start),actor)
    schedule=svc.create_schedule(SurgeryScheduleCreate(booking_id=booking.id,room_id=room.id,scheduled_start_at=start,scheduled_end_at=start+timedelta(hours=1)),actor)
    assert any(s.id==schedule.id for s in svc.list_schedules(actor,date(2026,11,2)))
    assert not any(s.id==schedule.id for s in svc.list_schedules(actor,date(2026,11,1)))


def test_grouped_blood_stock_totals_include_more_than_detail_limit(db):
    actor,_,_,_=seed(db)
    db.add_all([BloodUnit(branch_id=actor.branch_id,unit_number='GROUP-'+uuid4().hex,blood_group='A+',component_type='Whole Blood',status='available',testing_status='completed',expiry_date=date.today()+timedelta(days=10)) for _ in range(501)])
    db.commit()
    rows=BloodBankService(db,actor).report('blood_group_stock',None,None).rows
    assert len(rows)==1 and rows[0]['units']==501
