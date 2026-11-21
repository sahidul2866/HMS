"""Prescription lifecycle on existing OPD visits; clinical and financial state stay independent."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select,func,or_
from app.core.exceptions import AppException
from app.models.configuration import ConfigurationProfile
from app.models.prescription import PrescriptionRevision, OPDExternalPayment, PrescriptionShortcut, PrescriptionEvent
from app.models.encounter import OPDVisit
from app.modules.audit.service import AuditService
from app.schemas.prescription import FormField, validate_layout

CLINICAL_FIELDS = ('chief_complaint','history_of_present_illness','past_history','vital_signs','examination_note','provisional_diagnosis','final_diagnosis','follow_up_date','follow_up_note','note')


def audit(db, visit, actor, kind, detail=None):
    values={key:(getattr(visit,key).isoformat() if hasattr(getattr(visit,key),'isoformat') else getattr(visit,key)) for key in CLINICAL_FIELDS}
    values.update({'prescription_data':visit.prescription_data,'clinical_version':visit.clinical_version,'prescription_status':visit.prescription_status})
    db.add(PrescriptionEvent(visit_id=visit.id,actor_id=actor.id,kind=kind,detail={**(detail or {}),'after':values},created_by=actor.id,updated_by=actor.id))
    AuditService(db).log(actor.id, 'prescription.'+kind, 'opd', 'opd_visit', str(visit.id), detail or {}, {})


def active_external_amount(db,visit_id):
    rejected={event.detail.get('claim_id') for event in db.scalars(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==visit_id,PrescriptionEvent.kind=='external_payment_review')) if event.detail.get('decision')=='rejected'}
    return sum((row.amount for row in db.scalars(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==visit_id,OPDExternalPayment.kind=='doctor_direct')) if str(row.id) not in rejected),Decimal(0))


def lock_visit(db, visit):
    db.refresh(visit, with_for_update={'of':OPDVisit})
    db.expire(visit,['orders'])


def assert_draft(visit):
    if visit.prescription_status in {'finalized','voided'}:
        raise AppException(409,'prescription_signed','Signed prescriptions require an explicit amendment; voided prescriptions are read-only')


def assert_signer(visit, actor):
    if visit.consulting_doctor_user_id != actor.id or not any(r.is_active and r.is_doctor_role for r in actor.roles):
        raise AppException(403,'prescription_signer','Only the assigned doctor can sign or amend this prescription')


def templates(db, visit):
    doctor=visit.consulting_doctor
    rows = list(db.scalars(select(ConfigurationProfile).where(ConfigurationProfile.profile_type=='prescription_layout',ConfigurationProfile.is_active.is_(True),or_(ConfigurationProfile.branch_id.is_(None),ConfigurationProfile.branch_id==visit.branch_id),or_(ConfigurationProfile.target_id.is_(None),ConfigurationProfile.target_id==visit.consulting_doctor_user_id,ConfigurationProfile.target_id==getattr(doctor,'department_id',None)))))
    matches=[]
    for row in rows:
        if row.branch_id not in {None,visit.branch_id}: continue
        if row.scope=='doctor' or row.target_type=='doctor':
            if row.target_id is None and row.is_default:rank=1
            elif row.target_id==visit.consulting_doctor_user_id:rank=3
            else:continue
        elif row.scope=='department' or row.target_type=='department':
            if row.target_id != getattr(doctor,'department_id',None) or row.target_id is None: continue
            rank=2
        elif row.target_id: continue
        else: rank=1
        matches.append((rank,row.branch_id is not None,row.is_default,row.updated_at,str(row.id),row))
    return [entry[-1] for entry in sorted(matches,key=lambda e:e[:-1],reverse=True)]


def resolve_template(db, visit):
    available=templates(db,visit)
    if visit.prescription_template_id:
        found=next((p for p in available if p.id==visit.prescription_template_id),None)
        if not found: raise AppException(422,'prescription_template_scope','Template is unavailable for this doctor or department')
        return found
    return available[0] if available else None


def validate_content(visit, template):
    data=visit.prescription_data or {}
    if len(str(data))>500000: raise AppException(422,'prescription_content_size','Prescription is too large')
    if not template:return
    values={**{key:getattr(visit,key) for key in CLINICAL_FIELDS},**data}
    for raw in template.payload.get('fields',[]):
        field=FormField.model_validate(raw)
        visible=field.visible and (not field.show_when or all(values.get(key)==value for key,value in field.show_when.items()))
        if not visible:continue
        if field.type in {'medicine_rows','investigation_rows'}:
            kind='prescription' if field.type=='medicine_rows' else 'investigation'
            rows=[row for row in visit.orders if row.order_type==kind and row.status!='cancelled' and not (row.prescription_detail or {}).get('_withdrawn_from_rx')]
            if field.required and not rows:raise AppException(422,'prescription_required',f'{field.label} requires at least one confirmed clinical order')
            continue
        value=values.get(field.key,field.default)
        if field.required and (value is None or value=='' or value==[]):
            raise AppException(422,'prescription_required',f'{field.label} is required')
        if value is None or value=='':continue
        if len(str(value))>field.max_length:raise AppException(422,'prescription_field_length',f'{field.label} is too long')
        if field.type=='number':
            try:number=Decimal(str(value))
            except Exception:raise AppException(422,'prescription_number',f'{field.label} must be a number')
            if not number.is_finite() or (field.min is not None and number<field.min) or (field.max is not None and number>field.max):raise AppException(422,'prescription_range',f'{field.label} is outside its allowed range')
        if field.type in {'select','searchable_select','radio'} and field.options and value not in field.options:raise AppException(422,'prescription_option',f'{field.label} has an invalid choice')
        if field.type=='date':
            from datetime import date
            try:date.fromisoformat(str(value))
            except ValueError:raise AppException(422,'prescription_date',f'{field.label} must be a valid date')


def sign(db,visit,actor):
    assert_signer(visit,actor)
    template=resolve_template(db,visit)
    validate_content(visit,template)
    if template:visit.prescription_template_id=template.id
    prior=db.scalar(select(PrescriptionRevision).where(PrescriptionRevision.visit_id==visit.id).order_by(PrescriptionRevision.version.desc()).limit(1))
    now=datetime.now(UTC)
    doctor=visit.consulting_doctor
    snapshot={key:(getattr(visit,key).isoformat() if hasattr(getattr(visit,key),'isoformat') else getattr(visit,key)) for key in CLINICAL_FIELDS}
    snapshot.update({'visit_id':str(visit.id),'visit_number':visit.visit_number,'visit_date':visit.visit_date.isoformat(),'patient_id':str(visit.patient_id),'doctor_id':str(actor.id),'signed_at':now.isoformat(),'created_at':visit.created_at.isoformat(),
        'patient':{'first_name':visit.patient.first_name,'last_name':visit.patient.last_name,'patient_number':visit.patient.patient_number,'date_of_birth':str(visit.patient.date_of_birth or ''),'gender':visit.patient.gender,'phone':visit.patient.phone},
        'doctor':{key:getattr(doctor,key,None) for key in ['opd_bmdc_registration','opd_signature_image','full_name','opd_prescription_header_name','opd_prescription_header_degrees','opd_prescription_header_specialty','opd_prescription_header_workplace','opd_prescription_header_chamber','opd_prescription_header_phone','opd_prescription_header_address']},
        'department_name':visit.department_name,'consulting_doctor_name':visit.consulting_doctor_name,
        'prescription_data':visit.prescription_data or {},'template_id':str(template.id) if template else None,'template_version':template.version if template else None,'template_payload':template.payload if template else {},
        'orders':[{'id':str(o.id),'order_type':o.order_type,'service_area':o.service_area,'item_name':o.item_name,'instructions':o.instructions,'quantity':str(o.quantity),'prescription_detail':o.prescription_detail,'status':o.status,'created_at':o.created_at.isoformat()} for o in visit.orders if o.status!='cancelled' and not (o.prescription_detail or {}).get('_withdrawn_from_rx')]})
    version=prior.version+1 if prior else 1
    row=PrescriptionRevision(visit_id=visit.id,version=version,status='amended' if prior else 'finalized',doctor_id=actor.id,reason=(visit.prescription_data or {}).get('_amendment_reason'),snapshot=snapshot,signed_at=now,created_by=actor.id,updated_by=actor.id)
    db.add(row);visit.prescription_status='finalized';visit.clinical_version+=1
    audit(db,visit,actor,'signed',{'version':version,'template_version':snapshot['template_version']})
    db.flush()


class PrescriptionWorkflow:
    def __init__(self,db):self.db=db

    def visit(self,identity,actor):
        from app.modules.opd.service import OPDService
        return OPDService(self.db).get_visit(identity,actor)

    def history(self,identity,actor):
        self.visit(identity,actor)
        return list(self.db.scalars(select(PrescriptionRevision).where(PrescriptionRevision.visit_id==identity).order_by(PrescriptionRevision.version)))

    def amend(self,identity,payload,actor,void=False):
        visit=self.visit(identity,actor);lock_visit(self.db,visit);assert_signer(visit,actor)
        previous=self.history(identity,actor)
        if previous and previous[-1].doctor_id not in {None,actor.id}:raise AppException(403,'prescription_original_signer','Only the original prescribing doctor can revise this signed record')
        if visit.clinical_version!=payload.expected_version:raise AppException(409,'prescription_conflict','Another user changed this prescription; reload before editing')
        if visit.prescription_status!='finalized':raise AppException(409,'prescription_not_signed','Only signed prescriptions can be amended or voided')
        if void:
            prior=self.history(identity,actor)[-1]
            self.db.add(PrescriptionRevision(visit_id=visit.id,version=prior.version+1,status='voided',doctor_id=actor.id,reason=payload.reason,snapshot={**prior.snapshot,'void_reason':payload.reason,'voided_at':datetime.now(UTC).isoformat()},signed_at=datetime.now(UTC),created_by=actor.id,updated_by=actor.id))
        visit.prescription_status='voided' if void else 'amended'
        visit.clinical_version+=1
        visit.prescription_data={**(visit.prescription_data or {}),'_amendment_reason':payload.reason}
        audit(self.db,visit,actor,'voided' if void else 'amendment_opened',{'reason':payload.reason})
        self.db.commit();return visit

    def link_external_remittance(self, identity, claim_id, payload, actor):
        from app.modules.auth.service import AuthService
        from app.models.accounting import JournalEntry
        permissions=AuthService(self.db).get_effective_permissions(actor)
        if not {'billing.payment.collect','accounting.view'}.issubset(permissions):
            raise AppException(403,'external_remittance_access','Finance collection and accounting access are required')
        visit=self.visit(identity,actor);lock_visit(self.db,visit)
        claim=self.db.get(OPDExternalPayment,claim_id)
        if not claim or claim.visit_id!=identity or claim.kind!='doctor_direct':
            raise AppException(404,'external_payment_not_found','Doctor-direct payment claim not found')
        events=list(self.db.scalars(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==identity,PrescriptionEvent.kind.in_(['external_payment_review','external_remittance_link']))))
        related=[event for event in events if event.detail.get('claim_id')==str(claim.id)]
        for event in events:
            detail=event.detail
            if event.kind=='external_remittance_link' and detail.get('request_key')==payload.request_key:
                if detail.get('claim_id')!=str(claim.id) or detail.get('journal_id')!=str(payload.journal_id) or Decimal(detail['amount'])!=payload.amount or detail.get('evidence')!=payload.evidence:
                    raise AppException(409,'external_remittance_conflict','Request key already used for another remittance')
                return event
        if not any(event.kind=='external_payment_review' and event.detail.get('decision')=='verified' for event in related):
            raise AppException(409,'external_payment_unverified','Verify the external receipt before reconciling a remittance')
        entry=self.db.scalar(select(JournalEntry).where(JournalEntry.id==payload.journal_id).with_for_update())
        if not entry or entry.branch_id!=visit.branch_id or entry.branch_id!=actor.branch_id or entry.status!='posted':
            raise AppException(422,'external_remittance_journal','Choose a posted receipt in the consultation branch')
        reference=str(entry.source_reference or '')
        if entry.source_module!='opd_external_remittance' or not (reference==str(claim.id) or reference.startswith(str(claim.id)+':')):
            raise AppException(422,'external_remittance_reference','Receipt source must be opd_external_remittance and reference must start with this claim UUID')
        cash=sum((line.debit_amount-line.credit_amount for line in entry.lines if line.account_code in {'1001','1011','1012','1013','1020','1031','1032','1033','1034'}),Decimal(0))
        remitted=Decimal(0);linked=Decimal(0)
        for event in related:
            if event.kind!='external_remittance_link':continue
            previous=self.db.get(JournalEntry,UUID(event.detail['journal_id']))
            if previous and previous.status=='posted':
                remitted+=Decimal(event.detail['amount'])
                if previous.id==entry.id:linked+=Decimal(event.detail['amount'])
        due=Decimal(claim.settlement_snapshot.get('hospital_share_due') or '0')
        if payload.amount>due-remitted or payload.amount>cash-linked:
            raise AppException(422,'external_remittance_excess','Amount exceeds the remaining hospital share or unlinked cash in this receipt')
        # Link an actual existing posting. Never create a second cash receipt or invoice payment.
        detail={'claim_id':str(claim.id),'journal_id':str(entry.id),'journal_number':entry.journal_number,'amount':str(payload.amount),'evidence':payload.evidence,'request_key':payload.request_key,'hospital_share_due':str(due),'remaining_hospital_share':str(due-remitted-payload.amount),'new_hospital_cash_collected':'0.00'}
        event=PrescriptionEvent(visit_id=identity,actor_id=actor.id,kind='external_remittance_link',detail=detail,created_by=actor.id,updated_by=actor.id)
        self.db.add(event)
        AuditService(self.db).log(actor.id,'prescription.external_remittance_link','opd','opd_visit',str(identity),detail,{})
        self.db.commit();return event

    def review_external_payment(self, identity, claim_id, payload, actor):
        from app.modules.auth.service import AuthService
        if 'billing.payment.collect' not in AuthService(self.db).get_effective_permissions(actor):
            raise AppException(403,'external_review_access','A finance collector must verify external payment evidence')
        visit=self.visit(identity,actor)
        from app.models.branch import Branch
        if visit.branch_id:self.db.execute(select(Branch.id).where(Branch.id==visit.branch_id).with_for_update())
        lock_visit(self.db,visit)
        claim=self.db.get(OPDExternalPayment,claim_id)
        if not claim or claim.visit_id!=visit.id or claim.kind!='doctor_direct':
            raise AppException(404,'external_payment_not_found','Doctor-direct payment claim not found')
        events=list(self.db.scalars(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==identity,PrescriptionEvent.kind=='external_payment_review')))
        for event in events:
            detail=event.detail
            if detail.get('request_key')==payload.request_key:
                if detail.get('claim_id')!=str(claim.id) or detail.get('decision')!=payload.decision or detail.get('evidence')!=payload.evidence:
                    raise AppException(409,'external_review_conflict','Request key already used for another review')
                return event
            if detail.get('claim_id')==str(claim.id):
                raise AppException(409,'external_payment_reviewed','This immutable claim already has a finance decision')
        if payload.decision=='verified' and claim.settlement_snapshot.get('rule_status')=='configuration_required':
            raise AppException(422,'external_settlement_missing','No settlement rule was captured; resolve the claim through finance before verification')
        audit(self.db,visit,actor,'external_payment_review',{'claim_id':str(claim.id),'request_key':payload.request_key,'decision':payload.decision,'evidence':payload.evidence,'amount':str(claim.amount),'settlement_snapshot':claim.settlement_snapshot,'hospital_cash_collected':'0.00'})
        self.db.flush()
        event=self.db.scalar(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==identity,PrescriptionEvent.kind=='external_payment_review').order_by(PrescriptionEvent.created_at.desc()))
        if payload.decision=='verified':
            from app.modules.accounting.doctor_collections import post_verified_doctor_collection
            post_verified_doctor_collection(self.db,claim,visit,actor)
        self.db.commit();return event

    def external_payment(self,identity,payload,actor):
        visit=self.visit(identity,actor)
        # Same branch-first lock order as billing commands prevents simultaneous double collection.
        from app.models.branch import Branch
        if visit.branch_id:self.db.execute(select(Branch.id).where(Branch.id==visit.branch_id).with_for_update())
        lock_visit(self.db,visit)
        from app.modules.auth.service import AuthService
        if actor.id!=visit.consulting_doctor_user_id and 'billing.payment.collect' not in AuthService(self.db).get_effective_permissions(actor):raise AppException(403,'external_payment_access','Only the assigned doctor or an authorized cashier can record consultation payment information')
        prior=self.db.scalar(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==identity,OPDExternalPayment.request_key==payload.request_key))
        if prior:
            if prior.kind!=payload.kind or prior.amount!=payload.amount or prior.reason!=payload.reason:raise AppException(409,'external_payment_conflict','Request key already used for different payment information')
            return visit
        from app.models.billing import BillingInvoice
        invoice=self.db.scalar(select(BillingInvoice).where(BillingInvoice.source_opd_visit_id==visit.id,BillingInvoice.billing_stage=='opd',BillingInvoice.status=='posted'))
        if invoice and invoice.paid_amount>0:
            raise AppException(409,'consultation_already_collected','Hospital receipts already exist. Reconcile them through billing before recording a different payment source')
        received=active_external_amount(self.db,visit.id)
        if payload.kind=='doctor_direct' and (payload.amount<=0 or payload.amount>max(Decimal(0),visit.consultation_total-received)):
            raise AppException(422,'direct_payment_limit','Direct receipt must be positive and cannot exceed the remaining consultation amount')
        if payload.kind!='doctor_direct' and payload.amount:raise AppException(422,'external_payment_amount','Only doctor-direct receipts can have an amount')
        if payload.kind=='free' and visit.consultation_total:raise AppException(422,'consultation_not_free','Use an authorized fee waiver or billing discount for a chargeable consultation')
        # Capture the existing doctor-share configuration. A claim never posts hospital cash.
        share=Decimal(0);profiles=list(self.db.scalars(select(ConfigurationProfile).where(ConfigurationProfile.profile_type=='doctor_share',ConfigurationProfile.is_active.is_(True))))
        applicable=[p for p in profiles if p.branch_id in {None,visit.branch_id} and (p.target_id==visit.consulting_doctor_user_id or (p.is_default and not p.target_id))]
        applicable.sort(key=lambda p:(p.target_id is not None,p.updated_at),reverse=True)
        config=applicable[0] if applicable else None
        if config:
            rate=Decimal(str(config.payload.get('doctor_share_percentage',0)))
            if not 0<=rate<=100:raise AppException(422,'doctor_share_invalid','Doctor share configuration is invalid')
            share=(payload.amount*rate/100).quantize(Decimal('.01'))
            if config.payload.get('method')=='fixed':share=min(payload.amount,Decimal(str(config.payload.get('doctor_share_amount',0))))
        settlement={'verified':False,'source':payload.kind,'configuration_id':str(config.id) if config else None,'configuration_version':config.version if config else None,'doctor_share':str(share),'hospital_share_due':str(payload.amount-share),'hospital_cash_collected':'0.00'}
        if invoice and payload.kind=='doctor_direct':
            from app.modules.billing.policies import financial_values
            from app.schemas.billing_policy import FinancialRules
            from app.utils.billing_amounts import net_line_amounts,money
            lines=[item for item in invoice.items if item.source_module in {'opd','opd_visit'} and not item.source_opd_visit_order_id]
            net=net_line_amounts(invoice);values={};doctor_accounts=set()
            for item in lines:
                frozen=item.financial_snapshot or {}
                if not frozen.get('rules'):continue
                rules=FinancialRules.model_validate(frozen['rules'])
                if rules.doctor_key:doctor_accounts.add(rules.doctor_key)
                for (key,component),amount in financial_values(item,net[item.id],rules).items():values[key]=values.get(key,Decimal(0))+amount
            total=sum(values.values(),Decimal(0))
            if total>0:
                allocations={key:money(amount*payload.amount/total) for key,amount in values.items()}
                allocations['hospital']=allocations.get('hospital',Decimal(0))+payload.amount-sum(allocations.values())
                doctor_amount=sum((amount for key,amount in allocations.items() if key in doctor_accounts),Decimal(0))
                settlement={**settlement,'rule_source':'frozen_billing_invoice','invoice_id':str(invoice.id),'allocations':{key:str(amount) for key,amount in allocations.items()},'doctor_share':str(doctor_amount),'hospital_share_due':str(allocations.get('hospital',Decimal(0)))}
        if not config and 'rule_source' not in settlement:
            settlement={**settlement,'doctor_share':None,'hospital_share_due':None,'rule_status':'configuration_required'}
        row=OPDExternalPayment(visit_id=visit.id,kind=payload.kind,amount=payload.amount,request_key=payload.request_key,reason=payload.reason,settlement_snapshot=settlement,created_by=actor.id,updated_by=actor.id)
        self.db.add(row);visit.consultation_payment_source=payload.kind
        visit.consultation_payment_status={'doctor_direct':'doctor_direct','pending':'unpaid','waived':'waived','free':'free'}[payload.kind]
        audit(self.db,visit,actor,'payment_information',{'kind':payload.kind,'amount':str(payload.amount),'hospital_cash_collected':'0.00','reason':payload.reason})
        self.db.commit();return visit
