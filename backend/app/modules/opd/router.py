from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.opd.service import OPDService
from app.core.exceptions import AppException
from app.schemas.encounter import (
    IPDAdmissionRead,
    OPDConvertToIPD,
    OPDSummary,
    OPDVisitConsultationUpdate,
    OPDVisitCreate,
    OPDVisitPaymentUpdate,
    OPDVisitOrderCreate,
    OPDVisitOrderUpdate,
    OPDVisitRead,
    OPDVisitStatusUpdate,
    OPDVisitUpdate,
)

router = APIRouter(prefix="/opd", tags=["OPD"])


@router.get("/visits", response_model=list[OPDVisitRead], dependencies=[Depends(require_permissions("opd.view"))])
def list_opd_visits(doctor_user_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[OPDVisitRead]:
    return [OPDVisitRead.model_validate(item, from_attributes=True) for item in OPDService(db).list_visits(user, doctor_user_id)]


@router.get("/visits/{visit_id}", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.view"))])
def get_opd_visit(visit_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> OPDVisitRead:
    visit = OPDService(db).get_visit(visit_id, user)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.get("/summary", response_model=OPDSummary, dependencies=[Depends(require_permissions("opd.view"))])
def get_opd_summary(doctor_user_id: UUID | None = None, visit_date: date | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> OPDSummary:
    return OPDService(db).get_summary(user, doctor_user_id, visit_date)


@router.post("/visits", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.visit.create"))])
def create_opd_visit(
    payload: OPDVisitCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).create_visit(payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.visit.edit"))])
def update_opd_visit(
    visit_id: UUID,
    payload: OPDVisitUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).update_visit(visit_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.put(
    "/visits/{visit_id}/status",
    response_model=OPDVisitRead,
    dependencies=[Depends(require_permissions("opd.visit.manage"))],
)
def update_opd_status(
    visit_id: UUID,
    payload: OPDVisitStatusUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).update_status(visit_id, payload.status, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/payment", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("billing.payment.collect"))])
def update_opd_payment(
    visit_id: UUID,
    payload: OPDVisitPaymentUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).update_payment(visit_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.post("/visits/{visit_id}/orders", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.prescribe"))])
def create_opd_order(
    visit_id: UUID,
    payload: OPDVisitOrderCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).create_order(visit_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/orders/{order_id}", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.prescribe"))])
def update_opd_order(
    visit_id: UUID,
    order_id: UUID,
    payload: OPDVisitOrderUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).update_order(visit_id, order_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.delete("/visits/{visit_id}/orders/{order_id}", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.prescribe"))])
def delete_opd_order(
    visit_id: UUID,
    order_id: UUID,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).delete_order(visit_id, order_id, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/consultation", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.prescribe"))])
def update_opd_consultation(
    visit_id: UUID,
    payload: OPDVisitConsultationUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).update_consultation(visit_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.post("/visits/{visit_id}/finalize", response_model=OPDVisitRead, dependencies=[Depends(require_permissions("opd.prescribe"))])
def finalize_opd_prescription(
    visit_id: UUID,
    payload: OPDVisitConsultationUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OPDVisitRead:
    visit = OPDService(db).finalize_prescription(visit_id, payload, user, context)
    return OPDVisitRead.model_validate(visit, from_attributes=True)


@router.post(
    "/visits/{visit_id}/convert-to-ipd",
    response_model=IPDAdmissionRead,
    dependencies=[Depends(require_any_permissions("ipd.admit", "ipd.admission.manage"))],
)
def convert_opd_to_ipd(
    visit_id: UUID,
    payload: OPDConvertToIPD,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = OPDService(db).convert_to_ipd(visit_id, payload, user, context)
    return IPDAdmissionRead.model_validate(admission, from_attributes=True)

from app.modules.opd.prescriptions import PrescriptionWorkflow, templates
from app.schemas.prescription import ExternalRemittanceLink, ExternalPaymentReview, PrescriptionAction, DirectConsultationPayment, ClinicalShortcut
from app.models.prescription import PrescriptionShortcut, OPDExternalPayment
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from decimal import Decimal


def clinical_row(row):
    return jsonable_encoder({column.name:getattr(row,column.name) for column in row.__table__.columns},custom_encoder={Decimal:str})


@router.get('/visits/{visit_id}/prescription-history',dependencies=[Depends(require_permissions('opd.view'))])
def prescription_history(visit_id:UUID,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [clinical_row(row) for row in PrescriptionWorkflow(db).history(visit_id,user)]


@router.post('/visits/{visit_id}/prescription-amend',response_model=OPDVisitRead,dependencies=[Depends(require_permissions('opd.prescribe'))])
def amend_prescription(visit_id:UUID,payload:PrescriptionAction,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return PrescriptionWorkflow(db).amend(visit_id,payload,user)


@router.post('/visits/{visit_id}/prescription-void',response_model=OPDVisitRead,dependencies=[Depends(require_permissions('opd.prescribe'))])
def void_prescription(visit_id:UUID,payload:PrescriptionAction,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return PrescriptionWorkflow(db).amend(visit_id,payload,user,void=True)


@router.get('/visits/{visit_id}/prescription-templates',dependencies=[Depends(require_permissions('opd.prescribe'))])
def visit_prescription_templates(visit_id:UUID,user=Depends(get_current_user),db:Session=Depends(get_db)):
    visit=PrescriptionWorkflow(db).visit(visit_id,user)
    return [clinical_row(row) for row in templates(db,visit)]


@router.post('/visits/{visit_id}/external-payment',response_model=OPDVisitRead,dependencies=[Depends(require_any_permissions('opd.prescribe','billing.payment.collect'))])
def external_consultation_payment(visit_id:UUID,payload:DirectConsultationPayment,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return PrescriptionWorkflow(db).external_payment(visit_id,payload,user)


@router.get('/visits/{visit_id}/external-payments',dependencies=[Depends(require_permissions('opd.view'))])
def external_payment_records(visit_id:UUID,user=Depends(get_current_user),db:Session=Depends(get_db)):
    PrescriptionWorkflow(db).visit(visit_id,user)
    from app.models.accounting import JournalEntry
    from app.models.prescription import PrescriptionEvent
    events=list(db.scalars(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==visit_id,PrescriptionEvent.kind.in_(['external_payment_review','external_remittance_link']))))
    result=[]
    for row in db.scalars(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==visit_id)):
        related=[event for event in events if event.detail.get('claim_id')==str(row.id)]
        review=next((event.detail for event in related if event.kind=='external_payment_review'),None)
        from decimal import Decimal
        remitted=Decimal(0)
        for event in related:
            if event.kind!='external_remittance_link':continue
            journal=db.get(JournalEntry,UUID(event.detail['journal_id']))
            if journal and journal.status=='posted':remitted+=Decimal(event.detail['amount'])
        due=row.settlement_snapshot.get('hospital_share_due')
        result.append({**clinical_row(row),'finance_review':review,'hospital_share_remitted':str(remitted),'hospital_share_remaining':str(Decimal(due)-remitted) if due is not None else None})
    return result


@router.get('/prescription-shortcuts',dependencies=[Depends(require_permissions('opd.prescribe'))])
def prescription_shortcuts(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [clinical_row(row) for row in db.scalars(select(PrescriptionShortcut).where(PrescriptionShortcut.owner_id==user.id,PrescriptionShortcut.is_active.is_(True)))]


@router.post('/prescription-shortcuts',dependencies=[Depends(require_permissions('opd.prescribe'))])
def save_prescription_shortcut(payload:ClinicalShortcut,user=Depends(get_current_user),db:Session=Depends(get_db)):
    row=PrescriptionShortcut(owner_id=user.id,branch_id=user.branch_id,**payload.model_dump(),created_by=user.id,updated_by=user.id)
    db.add(row);db.commit();return clinical_row(row)


@router.delete('/prescription-shortcuts/{shortcut_id}',dependencies=[Depends(require_permissions('opd.prescribe'))])
def remove_prescription_shortcut(shortcut_id:UUID,user=Depends(get_current_user),db:Session=Depends(get_db)):
    row=db.get(PrescriptionShortcut,shortcut_id)
    if not row or row.owner_id!=user.id:raise AppException(404,'shortcut_not_found','Shortcut not found')
    row.is_active=False;db.commit();return {'deleted':True}


@router.post('/visits/{visit_id}/orders-batch',response_model=OPDVisitRead,dependencies=[Depends(require_permissions('opd.prescribe'))])
def create_prescription_combination(visit_id:UUID,payload:list[OPDVisitOrderCreate],user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.core.exceptions import AppException
    if not 1<=len(payload)<=50:raise AppException(422,'prescription_batch_size','Choose between one and fifty confirmed orders')
    service=OPDService(db)
    for order in payload:service.create_order(visit_id,order,user,{},commit=False)
    db.commit();return service.get_visit(visit_id,user)


@router.get('/prescribing-history',dependencies=[Depends(require_permissions('opd.prescribe'))])
def prescribing_history(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.encounter import OPDVisit,OPDVisitOrder
    from sqlalchemy import func
    base=select(OPDVisitOrder.item_name,OPDVisitOrder.order_type,func.count(OPDVisitOrder.id).label('uses'),func.max(OPDVisitOrder.created_at).label('last_used')).join(OPDVisit,OPDVisit.id==OPDVisitOrder.visit_id).where(OPDVisit.consulting_doctor_user_id==user.id,OPDVisitOrder.status!='cancelled')
    if user.branch_id:base=base.where(OPDVisit.branch_id==user.branch_id)
    grouped=base.group_by(OPDVisitOrder.item_name,OPDVisitOrder.order_type)
    frequent=[dict(row._mapping) for row in db.execute(grouped.order_by(func.count(OPDVisitOrder.id).desc(),func.max(OPDVisitOrder.created_at).desc()).limit(12))]
    recent=[dict(row._mapping) for row in db.execute(grouped.order_by(func.max(OPDVisitOrder.created_at).desc()).limit(12))]
    return {'frequent':frequent,'recent':recent}


@router.get('/visits/{visit_id}/prescription-audit',dependencies=[Depends(require_permissions('opd.view'))])
def prescription_audit_history(visit_id:UUID,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.prescription import PrescriptionEvent
    PrescriptionWorkflow(db).visit(visit_id,user)
    return [clinical_row(row) for row in db.scalars(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==visit_id).order_by(PrescriptionEvent.created_at,PrescriptionEvent.id))]


@router.post('/visits/{visit_id}/external-payments/{claim_id}/review',dependencies=[Depends(require_permissions('billing.payment.collect'))])
def review_external_payment(visit_id:UUID,claim_id:UUID,payload:ExternalPaymentReview,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return clinical_row(PrescriptionWorkflow(db).review_external_payment(visit_id,claim_id,payload,user))


@router.post('/visits/{visit_id}/external-payments/{claim_id}/remittances',dependencies=[Depends(require_permissions('billing.payment.collect','accounting.view'))])
def link_external_remittance(visit_id:UUID,claim_id:UUID,payload:ExternalRemittanceLink,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return clinical_row(PrescriptionWorkflow(db).link_external_remittance(visit_id,claim_id,payload,user))
