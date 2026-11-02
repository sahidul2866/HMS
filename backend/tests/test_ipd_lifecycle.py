"""IPD bed turnover, stopped treatment and handover integrity."""
from datetime import UTC,datetime
from decimal import Decimal
import pytest
from sqlalchemy import select
from test_opd_workflow_integration import database,db,seed  # noqa: F401
from app.core.exceptions import AppException
from app.models.encounter import IPDBed,IPDMedicationAdministration,IPDNursingTask
from app.modules.ipd.service import IPDService
from app.schemas.encounter import (IPDAdmissionCreate,IPDBedStatusUpdate,IPDOrderCreate,IPDOrderStatusUpdate,
    IPDMedicationAdministrationCreate,IPDNursingTaskUpdate,IPDHandoverCreate,IPDClinicalNoteCreate)


def scenario(db):
    actor,doctors,patient,_=seed(db)
    bed=IPDBed(branch_id=actor.branch_id,ward_name='IPD Test Ward',bed_number='A-1',bed_type='General',daily_rate=Decimal(300),status='available')
    db.add(bed);db.flush();service=IPDService(db)
    payload=IPDAdmissionCreate(patient_id=patient.id,bed_id=bed.id,admitted_at=datetime.now(UTC),admission_type='General',ward_name=bed.ward_name,bed_number=bed.bed_number,attending_doctor_name=doctors[0].full_name)
    admission=service.create_admission(payload,actor,{})
    return actor,doctors,bed,admission,service,payload


def test_bed_turnover_cannot_release_an_occupied_bed(db):
    actor,_,bed,admission,service,_=scenario(db)
    with pytest.raises(AppException,match='Transfer or discharge'):
        service.update_bed_status(bed.id,IPDBedStatusUpdate(status='available',reason='Premature turnover'),actor,{})
    admission.status='discharged';bed.status='cleaning';db.flush()
    assert service.update_bed_status(bed.id,IPDBedStatusUpdate(status='available',reason='Cleaning inspected and completed'),actor,{}).status=='available'
    assert service.update_bed_status(bed.id,IPDBedStatusUpdate(status='maintenance',reason='Scheduled maintenance'),actor,{}).status=='maintenance'


def test_bed_name_cannot_bypass_occupancy(db):
    from app.models.patient import Patient
    actor,_,bed,_,service,payload=scenario(db)
    patient=Patient(branch_id=actor.branch_id,patient_number='IPD-SECOND',first_name='Second',last_name='Synthetic')
    db.add(patient);db.flush()
    with pytest.raises(AppException,match='not available'):
        service.create_admission(payload.model_copy(update={'patient_id':patient.id,'bed_id':None}),actor,{})


def test_stopping_order_cancels_pending_doses_and_tasks(db):
    actor,_,_,admission,service,_=scenario(db)
    order=service.create_order(admission.id,IPDOrderCreate(order_type='medicine',item_name='Synthetic medicine'),actor,{})
    service.update_order_status(admission.id,order.id,IPDOrderStatusUpdate(status='discontinued',reason='Treatment changed by doctor'),actor,{})
    assert db.scalar(select(IPDMedicationAdministration).where(IPDMedicationAdministration.order_id==order.id)).status=='skipped'
    assert db.scalar(select(IPDNursingTask).where(IPDNursingTask.order_id==order.id)).status=='cancelled'
    with pytest.raises(AppException,match='order is closed'):
        service.administer_medication(admission.id,IPDMedicationAdministrationCreate(order_id=order.id,medicine_name=order.item_name),actor,{})
    with pytest.raises(AppException,match='order is closed'):
        service.update_order_status(admission.id,order.id,IPDOrderStatusUpdate(status='active'),actor,{})


def test_new_orders_revoke_department_clearance_and_have_unique_numbers(db):
    actor,_,_,admission,service,_=scenario(db)
    admission.lab_clearance_status='cleared';db.flush()
    orders=[service.create_order(admission.id,IPDOrderCreate(order_type='lab',item_name='Synthetic investigation'),actor,{}) for _ in range(2)]
    assert admission.lab_clearance_status=='pending'
    from app.models.laboratory import LabOrder
    assert len({db.get(LabOrder,o.lab_order_id).order_number for o in orders})==2


def test_handover_only_designated_receiver_can_acknowledge_once(db):
    actor,doctors,_,admission,service,_=scenario(db)
    handover=service.create_handover(admission.id,IPDHandoverCreate(summary='Shift care instructions',receiver_user_id=doctors[0].id),actor,{})
    with pytest.raises(AppException,match='designated receiver'):
        service.acknowledge_handover(handover.id,actor,{})
    assert service.acknowledge_handover(handover.id,doctors[0],{}).status=='acknowledged'
    with pytest.raises(AppException,match='already been acknowledged'):
        service.acknowledge_handover(handover.id,doctors[0],{})


def test_closed_admission_rejects_task_and_order_changes(db):
    actor,_,_,admission,service,_=scenario(db)
    order=service.create_order(admission.id,IPDOrderCreate(order_type='monitoring',item_name='Synthetic round'),actor,{})
    task=db.scalar(select(IPDNursingTask).where(IPDNursingTask.order_id==order.id))
    admission.status='discharged';db.flush()
    for action in (
        lambda:service.update_order_status(admission.id,order.id,IPDOrderStatusUpdate(status='completed'),actor,{}),
        lambda:service.update_nursing_task(task.id,IPDNursingTaskUpdate(status='completed'),actor,{}),
    ):
        with pytest.raises(AppException,match='closed'):
            action()


def test_daily_billing_uses_dhaka_day_highest_recorded_rate(db):
    from app.models.encounter import IPDBedStay
    from app.modules.ipd.bed_charges import daily_charges
    from app.modules.billing.service import BillingServiceManager
    from app.schemas.billing import BillingInvoiceCreate,BillingInvoiceItemCreate
    actor,_,bed,admission,service,_=scenario(db)
    for stay in db.scalars(select(IPDBedStay).where(IPDBedStay.admission_id==admission.id)):db.delete(stay)
    admission.admitted_at=datetime(2026,10,1,17,59,tzinfo=UTC)
    admission.discharged_at=datetime(2026,10,3,0,tzinfo=UTC)
    for start,end,rate in [(admission.admitted_at,datetime(2026,10,2,10,tzinfo=UTC),100),(datetime(2026,10,2,10,tzinfo=UTC),datetime(2026,10,2,18,tzinfo=UTC),300),(datetime(2026,10,2,18,tzinfo=UTC),admission.discharged_at,200)]:
        db.add(IPDBedStay(admission_id=admission.id,bed_id=bed.id,ward_name=bed.ward_name,bed_number=bed.bed_number,daily_rate=rate,started_at=start,ended_at=end,estimated=False))
    db.flush()
    days=daily_charges(db,admission)
    assert [(str(d['date']),d['rate']) for d in days]==[('2026-10-01',100),('2026-10-02',300),('2026-10-03',200)]
    bed.daily_rate=999;db.flush()
    billing=BillingServiceManager(db)
    draft=billing.build_ipd_admission_draft(admission.id,actor,stage='final')
    invoice=billing.create_invoice(BillingInvoiceCreate(patient_id=admission.patient_id,source_ipd_admission_id=admission.id,billing_stage='ipd_final',items=[BillingInvoiceItemCreate(billing_service_id=i.billing_service_id,quantity=i.quantity,source_module=i.source_module,source_record_type=i.source_record_type,source_record_id=i.source_record_id,bed_charge_date=i.bed_charge_date) for i in draft.items]),actor,{})
    assert invoice.total_amount==600
    assert service.billing_summary(admission.id,actor).unbilled_bed_days==0


def test_free_bed_does_not_require_a_fabricated_invoice(db):
    from app.models.encounter import IPDBedStay
    actor,_,bed,admission,service,_=scenario(db)
    bed.daily_rate=0;admission.daily_charge=0
    for stay in db.scalars(select(IPDBedStay).where(IPDBedStay.admission_id==admission.id)):stay.daily_rate=0
    db.flush()
    checks=service.discharge_readiness(admission.id,actor).checks
    assert next(c['done'] for c in checks if c['key']=='billing')
    assert service.billing_summary(admission.id,actor).billing_status=='cleared'


def test_same_day_upgrade_bills_only_rate_difference_after_interim(db):
    from app.models.encounter import IPDBedStay
    from app.modules.billing.service import BillingServiceManager
    from app.schemas.billing import BillingInvoiceCreate,BillingInvoiceItemCreate
    actor,_,bed,admission,service,_=scenario(db);billing=BillingServiceManager(db)
    def post(stage):
        draft=billing.build_ipd_admission_draft(admission.id,actor,stage=stage)
        return billing.create_invoice(BillingInvoiceCreate(patient_id=admission.patient_id,source_ipd_admission_id=admission.id,billing_stage=draft.billing_stage,items=[BillingInvoiceItemCreate(billing_service_id=i.billing_service_id,quantity=i.quantity,carry_forward_item_id=i.carry_forward_item_id,source_label=i.source_label,source_module=i.source_module,source_record_type=i.source_record_type,source_record_id=i.source_record_id,bed_charge_date=i.bed_charge_date) for i in draft.items]),actor,{})
    assert post('interim').total_amount==300
    now=datetime.now(UTC)
    for stay in db.scalars(select(IPDBedStay).where(IPDBedStay.admission_id==admission.id,IPDBedStay.ended_at.is_(None))):stay.ended_at=now
    db.add(IPDBedStay(admission_id=admission.id,bed_id=bed.id,ward_name=bed.ward_name,bed_number=bed.bed_number,daily_rate=500,started_at=now,estimated=False));db.flush()
    final=post('final')
    assert final.total_amount==500
    assert sorted(item.unit_price for item in final.items)==[200,300]
    assert service.billing_summary(admission.id,actor).billed_bed_days==1
    assert service.billing_summary(admission.id,actor).unbilled_bed_days==0


def test_lab_verification_completes_inpatient_order_and_sample_task(db):
    from app.modules.laboratory.service import LaboratoryService
    from app.schemas.encounter import ClinicalInvestigationResultUpdate
    actor,_,_,admission,service,_=scenario(db)
    order=service.create_order(admission.id,IPDOrderCreate(order_type='lab',item_name='Synthetic verified lab test'),actor,{})
    with pytest.raises(AppException,match='must verify'):
        service.update_order_status(admission.id,order.id,IPDOrderStatusUpdate(status='completed'),actor,{})
    result=LaboratoryService(db).update_result(order.lab_order_id,ClinicalInvestigationResultUpdate(status='verified',result_text='Synthetic verified result'),actor,{})
    assert result.admission_id==admission.id and result.visit_id is None
    assert result.visit_number==admission.admission_number
    db.refresh(order)
    assert order.status=='completed'
    task=db.scalar(select(IPDNursingTask).where(IPDNursingTask.order_id==order.id))
    assert task.status=='completed'


def test_stopping_administered_medicine_keeps_the_delivered_charge(db):
    from app.modules.ipd.billing_rules import billable_order
    actor,_,_,admission,service,_=scenario(db)
    order=service.create_order(admission.id,IPDOrderCreate(order_type='medicine',item_name='Delivered medication'),actor,{})
    service.administer_medication(admission.id,IPDMedicationAdministrationCreate(order_id=order.id,medicine_name=order.item_name),actor,{})
    service.update_order_status(admission.id,order.id,IPDOrderStatusUpdate(status='discontinued',reason='Stop future doses'),actor,{})
    assert billable_order(db,order)
    assert service.billing_summary(admission.id,actor).unbilled_order_count==1
