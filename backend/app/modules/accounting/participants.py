"""Bridge approved billing allocations to the GL without recalculating economic shares."""
from datetime import date
from app.utils.accounting_time import today_local
from decimal import Decimal
from sqlalchemy import select
from app.models.billing_policy import BillingAllocation
from app.models.billing import BillingInvoice
from app.modules.accounting.controls import policy_for
from app.modules.accounting.service import AccountingService


def post_participant_allocations(db,actor):
    policy=policy_for(db,actor.branch_id,today_local())
    if not policy:return
    cutover=date.fromisoformat(policy.settings['cutover_date'])
    service=AccountingService(db)
    rows=list(db.scalars(select(BillingAllocation).where(BillingAllocation.branch_id==actor.branch_id,BillingAllocation.participant_key!='hospital',BillingAllocation.state.in_(['approved','settled']),BillingAllocation.created_at>=cutover).order_by(BillingAllocation.created_at,BillingAllocation.id)))
    for row in rows:
        if service._source_entry_exists(actor.branch_id,'billing_allocation',str(row.id)):continue
        invoice=db.get(BillingInvoice,row.invoice_id) if row.invoice_id else None
        context=[]
        if invoice:context=invoice.items
        else:
            previous=list(db.scalars(select(BillingAllocation).where(BillingAllocation.branch_id==actor.branch_id,BillingAllocation.participant_key==row.participant_key,BillingAllocation.invoice_id.is_not(None))))
            for prior in previous:
                original=db.get(BillingInvoice,prior.invoice_id)
                if original:context.extend(original.items)
        is_doctor=any((item.financial_snapshot or {}).get('rules',{}).get('doctor_key')==row.participant_key for item in context)
        payable='2110' if is_doctor else '2120'
        offset='5010' if is_doctor else '5020'
        settings=policy.settings
        if invoice:
            from app.models.operational_posting import OperationalPosting
            from app.models.accounting import JournalEntry
            original_post=db.scalar(select(OperationalPosting).where(OperationalPosting.invoice_id==invoice.id,OperationalPosting.event=='invoice'))
            original_journal=db.get(JournalEntry,original_post.journal_id) if original_post and original_post.journal_id else None
            if original_journal and (original_journal.policy_snapshot or {}).get('settings'):settings=original_journal.policy_snapshot['settings']
        if is_doctor and settings.get('consultation_role')=='agent':offset=settings.get('revenue_accounts',{}).get(invoice.source_module,'4000') if invoice else '4000'
        if row.component in {'settlement','direct_retention'}:
            amount=-Decimal(row.amount)
            if amount<=0:continue
            lines=[(payable,'Participant payable',amount,0),('1160' if row.component=='direct_retention' else policy.settings.get('settlement_account','1020'),'Approved settlement channel / retained collection',0,amount)]
        else:
            amount=Decimal(row.amount)
            if not amount:continue
            lines=[(offset,'Approved allocation recognition',amount,0),(payable,'Participant payable',0,amount)] if amount>0 else [(payable,'Participant adjustment',-amount,0),(offset,'Allocation reversal',0,-amount)]
        service._create_auto_entry(actor,'billing_allocation',str(row.id),today_local(),'Participant '+row.participant_key+' / '+row.component+' / '+row.reason,lines)
