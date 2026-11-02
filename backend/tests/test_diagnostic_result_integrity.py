"""Result text must survive reload; entry permission never grants approval."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from test_opd_workflow_integration import database, db, seed  # noqa: F401
from app.core.exceptions import AppException
from app.models.laboratory import LabOrder, LabOrderItem
from app.models.radiology import RadiologyOrder
from app.models.user import User
from app.models.permission import Permission
from app.modules.laboratory.service import LaboratoryService
from app.modules.radiology.service import RadiologyService
from app.schemas.encounter import ClinicalInvestigationResultUpdate


@pytest.mark.parametrize('kind,model,service_cls,enter_permission', [('laboratory',LabOrder,LaboratoryService,'laboratory.result.enter'),('radiology',RadiologyOrder,RadiologyService,'radiology.upload_report')])
def test_result_persistence_and_reviewer_separation(db,kind,model,service_cls,enter_permission):
    actor, _, patient, _=seed(db)
    order=model(branch_id=actor.branch_id,patient_id=patient.id,order_number='RESULT-'+uuid4().hex[:10],status='pending')
    if model is RadiologyOrder: order.study_description="Synthetic review study"
    db.add(order);db.flush()
    if kind=='laboratory':db.add(LabOrderItem(order_id=order.id,test_name='Narrative review',quantity=1))
    editor=User(branch_id=actor.branch_id,username='editor-'+uuid4().hex[:8],email=uuid4().hex[:8]+'@example.test',full_name='Entry only',hashed_password='unused',direct_permissions=list(db.scalars(select(Permission).where(Permission.code.in_([enter_permission,kind+'.view'])))))
    db.add(editor);db.commit()
    service=service_cls(db)
    with pytest.raises(AppException) as error:
        service.update_result(order.id,ClinicalInvestigationResultUpdate(status='verified',result_text='Unauthorized approval'),editor,{})
    assert error.value.status_code==403 and order.status=='pending'
    result=service.update_result(order.id,ClinicalInvestigationResultUpdate(status='completed',sample_note='Synthetic specimen note',result_text='Synthetic findings retained after reload'),editor,{})
    assert result.result_text=='Synthetic findings retained after reload'
    assert result.sample_note=='Synthetic specimen note'
    db.expire_all()
    reloaded=next(item for item in service.list_worklist(actor) if item.order_id==order.id)
    assert reloaded.result_text==result.result_text and reloaded.sample_note==result.sample_note
    # A status-only review must not erase the existing text.
    approved=service.update_result(order.id,ClinicalInvestigationResultUpdate(status='verified'),actor,{})
    assert approved.result_text==result.result_text and approved.verified_at
    with pytest.raises(AppException) as error:
        service.update_result(order.id,ClinicalInvestigationResultUpdate(status='completed',result_text='Overwrite approved findings'),editor,{})
    assert error.value.status_code==403
    if kind == 'radiology':
        from app.schemas.radiology import RadiologyReportUpsert
        with pytest.raises(AppException) as error:
            service.add_report(RadiologyReportUpsert(order_id=order.id, findings='Attempt to overwrite verified report'), editor, {})
        assert error.value.status_code == 403


@pytest.mark.parametrize('model,service_cls',[(LabOrder,LaboratoryService),(RadiologyOrder,RadiologyService)])
def test_empty_findings_cannot_be_verified(db,model,service_cls):
    actor,_,patient,_=seed(db)
    order=model(branch_id=actor.branch_id,patient_id=patient.id,order_number='EMPTY-'+uuid4().hex[:10],status='pending')
    if model is RadiologyOrder: order.study_description="Synthetic empty study"
    db.add(order);db.commit()
    with pytest.raises(AppException) as error:
        service_cls(db).update_result(order.id,ClinicalInvestigationResultUpdate(status='verified',result_text='  '),actor,{})
    assert error.value.code=='clinical_result_required' and order.status=='pending'
