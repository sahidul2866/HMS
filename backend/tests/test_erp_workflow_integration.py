"""Connected barcode, inpatient-care and financial lifecycle regression tests."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from test_opd_workflow_integration import database, db, seed, visit  # noqa: F401
from app.main import app
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.core.exceptions import AppException
from app.models.encounter import IPDBed, IPDAdmission, IPDOrder, IPDMedicationAdministration, OPDVisit
from app.models.branch import Branch
from app.models.patient import Patient
from app.models.billing import BillingItemConfig
from app.modules.ipd.service import IPDService
from app.modules.scanner.service import ScannerService
from app.schemas.scanner import ScanResolveRequest, ScanCodeCreate
from app.schemas.encounter import IPDAdmissionCreate, IPDOrderCreate, IPDMedicationAdministrationCreate, IPDClinicalNoteCreate


def test_connected_patient_to_ipd_care_final_payment_and_discharge(db):
    actor, doctors, _, slot = seed(db)
    beds = [IPDBed(branch_id=actor.branch_id, ward_name='ERP Test Ward', bed_number=f'ERP-{i}', bed_type='General', daily_rate=Decimal('300'), status='available') for i in range(2)]
    db.add_all(beds)
    db.flush()
    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: actor
    client = TestClient(app)
    def call(method, route, payload=None):
        response = client.request(method, '/api/v1'+route, json=payload) if payload is not None else client.request(method, '/api/v1'+route)
        assert response.status_code == 200, response.text
        return response.json()
    def resolve(code, expected_type, patient_id):
        result = call('POST','/scanner/resolve',{'code':code,'expected_record_type':expected_type,'expected_patient_id':patient_id})
        assert result['success'],result
        assert result['match_count'] == 1
        return result['records'][0]
    def invoice_from_draft(draft):
        assert draft['items']
        assert all(item['billing_service_id'] for item in draft['items']), draft
        return call('POST','/billing/invoices',{'patient_id':draft['patient_id'],'source_opd_visit_id':draft.get('source_opd_visit_id'),'source_ipd_admission_id':draft.get('source_ipd_admission_id'),'source_module':draft['source_module'],'billing_stage':draft['billing_stage'],'items':[{'billing_service_id':item['billing_service_id'],'quantity':item['quantity'],'source_module':item.get('source_module'),'source_opd_visit_order_id':item.get('source_opd_visit_order_id'),'source_record_type':item.get('source_record_type'),'source_record_id':item.get('source_record_id'),'bed_charge_date':item.get('bed_charge_date'),'source_label':item.get('source_label')} for item in draft['items']]})
    try:
        patient = call('POST','/patients',{'first_name':'ERP Synthetic','last_name':'Lifecycle','phone':'018'+uuid4().hex[:8].translate(str.maketrans('abcdef','123456'))})
        patient_id = patient['id']
        assert resolve(patient['patient_number'],'patient',patient_id)['record_id'] == patient_id
        booked = call('POST','/appointments',{'patient_id':patient_id,'doctor_user_id':str(doctors[0].id),'slot_start_at':slot.isoformat()})
        appointment_record = resolve(booked['appointment_number'],'appointment',patient_id)
        assert appointment_record['query_params']['appointmentId'] == booked['id']
        current = call('POST',f'/appointments/{booked["id"]}/check-in',{'department_name':'Medicine'})
        record = resolve(current['visit_number'],'opd_visit',patient_id)
        assert record['query_params']['openVisit'] == current['id']
        # Catalog synchronization is invoked by the same catalog endpoint as the browser.
        call('GET','/billing/services')
        invoice = invoice_from_draft(call('GET',f'/billing/drafts/opd-visit/{current["id"]}'))
        call('POST',f'/billing/invoices/{invoice["id"]}/payments',{'amount':invoice['total_amount'],'payment_method':'cash'})
        assert resolve(invoice['invoice_number'],'billing_invoice',patient_id)['query_params']['invoiceId'] == invoice['id']
        token = call('POST',f'/queue/call-next?queue_scope=opd&doctor_user_id={doctors[0].id}')
        assert token['visit_id'] == current['id']
        call('PUT',f'/opd/visits/{current["id"]}/status',{'status':'in_consultation'})
        call('POST',f'/opd/visits/{current["id"]}/orders',{'order_type':'prescription','item_name':'Synthetic prescription item','instructions':'Test-only record'})
        call('POST',f'/opd/visits/{current["id"]}/finalize',{'final_diagnosis':'Synthetic workflow diagnosis'})
        admission = call('POST',f'/opd/visits/{current["id"]}/convert-to-ipd',{'bed_id':str(beds[0].id),'admitted_at':datetime.now(UTC).isoformat(),'admission_type':'General','ward_name':'ERP Test Ward','bed_number':beds[0].bed_number,'attending_doctor_name':doctors[0].full_name})
        admission_id = admission['id']
        assert resolve(admission['admission_number'],'ipd_admission',patient_id)['route'].endswith(admission_id)
        call('POST',f'/ipd/admissions/{admission_id}/clinical-notes',{'note':'Synthetic inpatient assessment','diagnosis':'Synthetic workflow diagnosis'})
        call('POST',f'/ipd/admissions/{admission_id}/nursing-notes',{'note':'Synthetic nursing round','pulse':80,'spo2':98,'systolic_bp':120,'diastolic_bp':80})
        monitoring = call('POST',f'/ipd/admissions/{admission_id}/orders',{'order_type':'monitoring','item_name':'Synthetic monitoring task'})
        assert monitoring['billing_status'] == 'not_applicable'
        medicine = call('POST',f'/ipd/admissions/{admission_id}/orders',{'order_type':'medicine','item_name':'ERP Test Medication','scheduled_at':datetime.now(UTC).isoformat()})
        call('POST',f'/ipd/admissions/{admission_id}/medications',{'order_id':medicine['id'],'medicine_name':medicine['item_name'],'scheduled_at':medicine['scheduled_at'],'status':'administered'})
        workspace = call('GET',f'/ipd/admissions/{admission_id}/workspace')
        matching = [item for item in workspace['medications'] if item['order_id'] == medicine['id']]
        assert len(matching) == 1 and matching[0]['status'] == 'administered'
        # A dedicated billable catalog entry allows deterministic reconciliation of this synthetic item.
        db.add(BillingItemConfig(branch_id=actor.branch_id,source_module='pharmacy',source_entity_id=uuid4(),service_code='ERP-MED',service_name='ERP Test Medication',unit_price=Decimal('50'),doctor_share_percentage=0))
        db.flush()
        call('PATCH',f'/ipd/admissions/{admission_id}/orders/{medicine["id"]}',{'status':'completed'})
        handover = call('POST',f'/ipd/admissions/{admission_id}/handovers',{'summary':'Synthetic handover','receiver_user_id':str(actor.id)})
        call('POST',f'/ipd/handovers/{handover["id"]}/acknowledge')
        call('PUT',f'/ipd/admissions/{admission_id}/transfer',{'bed_id':str(beds[1].id),'ward_name':'ERP Test Ward','bed_number':beds[1].bed_number,'transfer_reason':'Synthetic bed transfer'})
        assert db.get(IPDBed,beds[0].id).status == 'cleaning'
        assert db.get(IPDBed,beds[1].id).status == 'occupied'
        call('POST',f'/ipd/admissions/{admission_id}/discharge-plan?status=requested')
        draft = call('GET',f'/billing/drafts/ipd-admission/{admission_id}?stage=final')
        final_invoice = invoice_from_draft(draft)
        call('POST',f'/billing/invoices/{final_invoice["id"]}/payments',{'amount':final_invoice['total_amount'],'payment_method':'cash'})
        readiness = call('GET',f'/ipd/admissions/{admission_id}/discharge-readiness')
        assert not any(item['key']=='billing' and not item['done'] for item in readiness['checks'])
        assert db.scalar(select(OPDVisit.id).where(OPDVisit.patient_id == db.get(IPDAdmission,admission_id).patient_id, OPDVisit.id != current['id'])) is None
        call('POST',f'/ipd/admissions/{admission_id}/discharge-plan?status=approved')
        discharged = call('PUT',f'/ipd/admissions/{admission_id}/discharge',{'discharge_condition':'Stable test record','discharge_diagnosis':'Synthetic diagnosis','discharge_summary':'Synthetic completed hospital journey'})
        assert discharged['status'] == 'discharged'
        assert db.get(IPDBed,beds[1].id).status == 'cleaning'
        assert db.get(OPDVisit,current['id']).converted_ipd_admission_id == db.get(IPDAdmission,admission_id).id
    finally:
        app.dependency_overrides.clear();app.dependency_overrides.update(original);client.close()


def test_barcode_rejects_wrong_patient_other_branch_and_preserves_clinical_scope(db):
    actor, doctors, patient, slot = seed(db)
    other_branch = Branch(code='OTHER',name='Other test branch')
    db.add(other_branch);db.flush()
    other = Patient(branch_id=other_branch.id,patient_number='ERP-FOREIGN',first_name='Other',last_name='Patient')
    db.add(other);db.flush()
    scanner = ScannerService(db)
    mismatch = scanner.resolve(ScanResolveRequest(code=patient.patient_number,expected_patient_id=other.id),actor)
    assert not mismatch.success and not mismatch.records
    denied = scanner.resolve(ScanResolveRequest(code=other.patient_number),actor)
    assert not denied.success and not denied.records
    with pytest.raises(AppException):
        scanner.create_code(ScanCodeCreate(record_type='patient',record_id=other.id,purpose='card'),actor)
    current = visit(db,actor,doctors[1],patient,slot)
    denied_doctor = scanner.resolve(ScanResolveRequest(code=current.visit_number),doctors[0])
    assert not denied_doctor.success and not denied_doctor.records


def test_closed_admission_and_cross_admission_medication_are_rejected(db):
    actor,doctors,patient,_ = seed(db)
    service = IPDService(db)
    admission = service.create_admission(IPDAdmissionCreate(patient_id=patient.id,admitted_at=datetime.now(UTC),admission_type='General',ward_name='Test',bed_number='B1',attending_doctor_name=doctors[0].full_name),actor,{})
    with pytest.raises(AppException,match='must belong'):
        service.administer_medication(admission.id,IPDMedicationAdministrationCreate(order_id=uuid4(),medicine_name='Synthetic medication'),actor,{})
    admission.status='discharged';db.commit()
    with pytest.raises(AppException,match='closed'):
        service.create_clinical_note(admission.id,IPDClinicalNoteCreate(note='Should be rejected'),actor,{})
