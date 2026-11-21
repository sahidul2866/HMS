"""Posted GL analysis plus explicitly labelled operational subledger reconciliation."""
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select,func,case,or_
from app.models.accounting import Account,JournalEntry,JournalEntryLine,SupplierInvoice,CorporateBill,InsuranceClaim
from app.models.billing import BillingInvoice,BillingRefund
from app.models.billing_policy import BillingAllocation
from app.models.accounting_control import AccountingPostingKey
from app.modules.accounting.controls import policy_for
from app.utils.accounting_time import today_local
from app.core.exceptions import AppException


class AccountingReports:
    def __init__(self,db):self.db=db
    def aging(self,actor,kind='patient',as_of=None):
        as_of=as_of or today_local();policy=policy_for(self.db,actor.branch_id,as_of)
        boundaries=(policy.settings if policy else {}).get('aging_days',[0,30,60,90])
        names=['Current']+[f'{boundaries[i-1]+1}–{boundaries[i]} days' for i in range(1,len(boundaries))]+[f'Over {boundaries[-1]} days']
        totals={name:Decimal(0) for name in names};rows=[]
        models={'patient':BillingInvoice,'supplier':SupplierInvoice,'corporate':CorporateBill,'insurance':InsuranceClaim}
        if kind not in models:raise AppException(422,'aging_kind','Choose patient, supplier, corporate or insurance')
        model=models[kind]
        for item in self.db.scalars(select(model).where(model.branch_id==actor.branch_id)):
            if item.status in {'void','cancelled','rejected','consolidated'}:continue
            issued=getattr(item,'invoice_date',None) or item.created_at.date()
            if issued>as_of:continue
            amount=Decimal(item.claim_amount-item.paid_amount) if kind=='insurance' else Decimal(item.due_amount)
            if kind=='patient' and item.source_opd_visit_id and item.billing_stage=='opd':
                from app.modules.opd.prescriptions import active_external_amount
                amount=max(Decimal(0),amount-active_external_amount(self.db,item.source_opd_visit_id))
            if amount<=0:continue
            due=getattr(item,'due_date',None) or issued
            days=(as_of-due).days
            bucket=names[0] if days<=0 else next((names[index] for index,boundary in enumerate(boundaries[1:],1) if days<=boundary),names[-1])
            totals[bucket]+=amount
            rows.append({'id':str(item.id),'reference':getattr(item,'invoice_number',None) or getattr(item,'bill_number',None) or getattr(item,'claim_number',None),'party':getattr(item,'supplier_name',None) or getattr(item,'company_name',None) or getattr(item,'provider_name',None) or str(getattr(item,'patient_id','')),'due_date':due.isoformat(),'days_overdue':max(0,days),'bucket':bucket,'amount':str(amount),'source_status':item.status})
        return {'basis':'Operational outstanding subledger; unposted records are shown with source status. Historical as-of collection reconstruction is not implied.','as_of':str(as_of),'rows':rows,'buckets':{name:str(amount) for name,amount in totals.items()},'total':str(sum(totals.values(),Decimal(0)))}

    def analysis(self,actor,kind,date_from=None,date_to=None):
        conditions=[JournalEntry.branch_id==actor.branch_id,JournalEntry.posting_applied_at.is_not(None),or_(JournalEntry.source_module.is_(None),JournalEntry.source_module!='year_end_close')]
        if date_from:conditions.append(JournalEntry.journal_date>=date_from)
        if date_to:conditions.append(JournalEntry.journal_date<=date_to)
        base=select(JournalEntryLine,JournalEntry,Account).join(JournalEntry,JournalEntryLine.journal_entry_id==JournalEntry.id).join(Account,Account.id==JournalEntryLine.account_id).where(*conditions)
        groups={}
        if kind in {'doctor_earnings','doctor_settlement','referral_commission'}:
            query=select(BillingAllocation).where(BillingAllocation.branch_id==actor.branch_id)
            if date_from:query=query.where(func.date(BillingAllocation.created_at)>=date_from)
            if date_to:query=query.where(func.date(BillingAllocation.created_at)<=date_to)
            rows=[]
            for item in self.db.scalars(query.order_by(BillingAllocation.created_at)):
                if kind=='doctor_settlement' and item.component not in {'settlement','direct_retention'}:continue
                if kind=='referral_commission' and item.component not in {'commission','approval','settlement'}:continue
                key=self.db.scalar(select(AccountingPostingKey.journal_id).where(AccountingPostingKey.branch_id==actor.branch_id,AccountingPostingKey.source_module=='billing_allocation',AccountingPostingKey.source_reference==str(item.id)))
                rows.append({'participant':item.participant_key,'component':item.component,'state':item.state,'amount':str(item.amount),'invoice_id':str(item.invoice_id) if item.invoice_id else '', 'journal_id':str(key) if key else '', 'posting_status':'posted' if key else 'unposted subledger','reason':item.reason})
            return {'basis':'Participant subledger, with explicit GL posting references; hospital and external collections are distinct','rows':rows}
        if kind in {'discount','refund_cancellation'}:
            rows=[]
            if kind=='discount':
                for invoice in self.db.scalars(select(BillingInvoice).where(BillingInvoice.branch_id==actor.branch_id,BillingInvoice.discount_amount>0)):
                    on=invoice.created_at.date()
                    if date_from and on<date_from or date_to and on>date_to:continue
                    rows.append({'invoice':invoice.invoice_number,'gross':str(invoice.sub_total),'discount':str(invoice.discount_amount),'net':str(invoice.total_amount),'status':invoice.status,'basis':'Economic discount; its GL treatment follows frozen allocations, not a separate assumed expense'})
            else:
                for refund in self.db.scalars(select(BillingRefund).where(BillingRefund.branch_id==actor.branch_id)):
                    on=refund.refunded_at.date()
                    if date_from and on<date_from or date_to and on>date_to:continue
                    rows.append({'reference':refund.refund_number,'invoice_id':str(refund.invoice_id),'kind':refund.refund_type,'credit_amount':str(refund.credit_amount),'cash_refunded':str(refund.amount),'reason':refund.reason})
            return {'basis':'Operational source documents; cash payouts and invoice credits are separate measures','rows':rows}
        revenue_codes={'opd_revenue':{'4010'},'ipd_revenue':{'4020','4070','4080'},'investigation_revenue':{'4030','4040','4050'},'pharmacy_margin':{'4200','5030'}}
        allowed={'department_profitability','branch_profitability','expense_analysis','service_revenue','monthly_summary','yearly_summary','payment_method_reconciliation','daily_collection',*revenue_codes}
        if kind not in allowed:raise AppException(422,'accounting_report','Unsupported analysis report')
        for line,entry,account in self.db.execute(base):
            debit=Decimal(line.debit_amount);credit=Decimal(line.credit_amount)
            if kind in revenue_codes:
                if account.account_code not in revenue_codes[kind]:continue
                key=account.name;value=credit-debit
            elif kind=='expense_analysis':
                if account.category not in {'expenses','expense'}:continue
                key=account.name;value=debit-credit
            elif kind in {'payment_method_reconciliation','daily_collection'}:
                if account.account_code not in {'1001','1011','1012','1013','1020','1031','1032','1033','1034'}:continue
                if kind=='daily_collection' and entry.source_module not in {'billing_payment','patient_advance','pharmacy_sale','opd_external_remittance','payment_adjustment'}:continue
                key=entry.journal_date.isoformat() if kind=='daily_collection' else account.name;value=debit-credit
            else:
                if account.category not in {'income','revenue','expenses','expense'}:continue
                value=credit-debit
                if kind=='department_profitability':key=line.cost_center or 'Unallocated department'
                elif kind=='branch_profitability':key=str(actor.branch_id)
                elif kind=='service_revenue':
                    if account.category not in {'income','revenue'}:continue
                    key=account.reporting_group or account.name
                elif kind=='monthly_summary':key=entry.journal_date.strftime('%Y-%m')
                else:key=entry.journal_date.strftime('%Y')
            groups[key]=groups.get(key,Decimal(0))+value
        return {'basis':'Posted GL movements; originals and their reversing entries are included. Unmapped service revenue remains in the general revenue account.','rows':[{'group':key,'net_amount':str(amount)} for key,amount in sorted(groups.items())],'total':str(sum(groups.values(),Decimal(0)))}
