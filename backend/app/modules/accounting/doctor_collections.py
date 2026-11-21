"""Verified doctor collections recognize receivables, never hospital cash."""
from datetime import date
from app.utils.accounting_time import today_local
from decimal import Decimal
from sqlalchemy import select
from app.models.billing import BillingInvoice
from app.modules.accounting.controls import policy_for
from app.modules.accounting.service import AccountingService
from app.core.exceptions import AppException


def post_verified_doctor_collection(db,claim,visit,actor):
    policy=policy_for(db,visit.branch_id,today_local())
    if not policy:return
    if actor.branch_id!=visit.branch_id:raise AppException(403,'doctor_collection_branch','Use the consultation branch for accounting verification')
    service=AccountingService(db)
    if service._source_entry_exists(actor.branch_id,'doctor_direct_collection',str(claim.id)):return
    retained=Decimal(claim.settlement_snapshot.get('doctor_share') or '0')
    invoice=db.scalar(select(BillingInvoice).where(BillingInvoice.source_opd_visit_id==visit.id,BillingInvoice.billing_stage=='opd',BillingInvoice.status=='posted'))
    if invoice:
        from app.models.operational_posting import OperationalPosting
        enrolled=db.scalar(select(OperationalPosting.id).where(OperationalPosting.invoice_id==invoice.id,OperationalPosting.event=='invoice'))
        if not enrolled:raise AppException(409,'doctor_collection_cutover','Reconcile the legacy consultation accrual before verifying the external collection')
        lines=[('1160','Doctor Receivable',claim.amount,0),('1100','Patient Accounts Receivable',0,claim.amount)]
        doctor_keys={(item.financial_snapshot or {}).get('rules',{}).get('doctor_key') for item in invoice.items}
        doctor_keys.discard(None)
        if retained and doctor_keys:
            from app.models.billing_policy import BillingAllocation
            from app.modules.accounting.participants import post_participant_allocations
            if len(doctor_keys)!=1:raise AppException(409,'doctor_retention_mapping','Reconcile the multi-doctor allocation before verifying direct collection')
            key=next(iter(doctor_keys))
            entries=list(db.scalars(select(BillingAllocation).where(BillingAllocation.branch_id==actor.branch_id,BillingAllocation.participant_key==key,BillingAllocation.state.in_(['approved','settled']))))
            available=sum((entry.amount for entry in entries),Decimal(0))
            if retained>available:raise AppException(409,'doctor_retention_settled','Doctor earnings are already settled or insufficient; reconcile prior payouts before verification')
            db.add(BillingAllocation(branch_id=actor.branch_id,invoice_id=invoice.id,participant_key=key,component='direct_retention',state='settled',amount=-retained,request_key='direct:'+str(claim.id),reason='Doctor retained own share of verified patient collection',created_by=actor.id,updated_by=actor.id))
            db.flush();post_participant_allocations(db,actor)
        elif retained:lines += [('5010','Doctor retained share',retained,0),('1160','Doctor retained share offset',0,retained)]
    elif policy.settings.get('consultation_role')=='agent':
        due=claim.amount-retained
        lines=[('1160','Doctor Receivable',due,0),('4010','Hospital consultation share',0,due)] if due else []
    else:
        lines=[('1160','Doctor Receivable',claim.amount,0),('4010','OPD Consultation Revenue',0,claim.amount)]
        if retained:lines += [('5010','Doctor Professional Fees',retained,0),('1160','Doctor retained share offset',0,retained)]
    if lines:service._create_auto_entry(actor,'doctor_direct_collection',str(claim.id),today_local(),'Verified direct collection for '+visit.visit_number,lines)
