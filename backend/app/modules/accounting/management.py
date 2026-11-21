"""COA, approved configuration, period controls and ledger-derived statements."""
from datetime import date
from decimal import Decimal
from sqlalchemy import select,func,or_,and_
from app.core.exceptions import AppException
from app.models.accounting import Account,JournalEntry,JournalEntryLine
from app.models.accounting_control import AccountingPolicy,FinancialPeriod
from app.modules.support_posting.service import lock_branch


class AccountingManagement:
    def __init__(self,db):self.db=db

    def audit(self,actor,action,identity,detail):
        from app.modules.accounting.service import AccountingService
        AccountingService(self.db)._audit(actor,action,'accounting_control',str(identity),{},detail)

    def propose_policy(self,payload,actor):
        lock_branch(self.db,actor)
        version=(self.db.scalar(select(func.max(AccountingPolicy.version)).where(AccountingPolicy.branch_id==actor.branch_id)) or 0)+1
        row=AccountingPolicy(branch_id=actor.branch_id,version=version,effective_from=payload.effective_from,settings=payload.settings.model_dump(mode='json'),approved_by=None,created_by=actor.id,updated_by=actor.id)
        self.db.add(row);self.db.flush();self.audit(actor,'accounting.policy.propose',row.id,{'version':version});self.db.commit();return row

    def approve_policy(self,identity,actor,reason):
        lock_branch(self.db,actor)
        row=self.db.scalar(select(AccountingPolicy).where(AccountingPolicy.id==identity,AccountingPolicy.branch_id==actor.branch_id).with_for_update())
        if not row:raise AppException(404,'policy_not_found','Accounting policy not found')
        if row.approved_by:return row
        if row.created_by==actor.id:raise AppException(403,'accounting_maker_checker','Another authorized accountant must approve the policy')
        row.approved_by=actor.id;row.updated_by=actor.id
        self.audit(actor,'accounting.policy.approve',row.id,{'reason':reason,'version':row.version});self.db.commit();return row

    def create_period(self,payload,actor):
        lock_branch(self.db,actor)
        if self.db.scalar(select(FinancialPeriod.id).where(FinancialPeriod.branch_id==actor.branch_id,FinancialPeriod.start_date<=payload.end_date,FinancialPeriod.end_date>=payload.start_date)):
            raise AppException(409,'financial_period_overlap','Financial periods cannot overlap')
        row=FinancialPeriod(**payload.model_dump(),branch_id=actor.branch_id,status='open',created_by=actor.id,updated_by=actor.id)
        self.db.add(row);self.db.flush();self.audit(actor,'accounting.period.create',row.id,{'name':row.name});self.db.commit();return row

    def period_action(self,identity,action,actor,reason):
        lock_branch(self.db,actor)
        row=self.db.scalar(select(FinancialPeriod).where(FinancialPeriod.id==identity,FinancialPeriod.branch_id==actor.branch_id).with_for_update())
        if not row:raise AppException(404,'period_not_found','Financial period not found')
        if action not in {'close','reopen'}:raise AppException(422,'period_action','Choose close or reopen')
        if action=='close':
            if not self.integrity(actor)['can_close']:raise AppException(409,'accounting_integrity_review','Resolve legacy GL, duplicate account codes or opening-balance differences before closing')
            if self.db.scalar(select(JournalEntry.id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.journal_date>=row.start_date,JournalEntry.journal_date<=row.end_date,JournalEntry.status.in_(['draft','submitted','approved'])).limit(1)):
                raise AppException(409,'period_pending_vouchers','Resolve pending vouchers before closing')
            statement=self.statements(actor,row.start_date,row.end_date)
            if Decimal(statement['total_debit'])!=Decimal(statement['total_credit']):raise AppException(409,'period_unbalanced','Trial balance is not balanced')
        row.status='closed' if action=='close' else 'open';row.updated_by=actor.id
        self.audit(actor,'accounting.period.'+action,row.id,{'reason':reason});self.db.commit();return row

    def update_account(self,identity,payload,actor):
        lock_branch(self.db,actor)
        row=self.db.scalar(select(Account).where(Account.id==identity,Account.branch_id==actor.branch_id).with_for_update())
        if not row:raise AppException(404,'account_not_found','Account not found')
        values=payload.model_dump(exclude_unset=True)
        if values.get('parent_id'):
            parent=self.db.get(Account,values['parent_id']);seen={row.id}
            if not parent or parent.branch_id!=actor.branch_id or not parent.is_control:raise AppException(422,'account_parent','Choose a branch control account')
            while parent:
                if parent.id in seen:raise AppException(422,'account_cycle','Account hierarchy cannot be cyclic')
                seen.add(parent.id);parent=self.db.get(Account,parent.parent_id) if parent.parent_id else None
        for key,value in values.items():setattr(row,key,value)
        row.updated_by=actor.id;self.audit(actor,'account.update',row.id,values);self.db.commit();return row

    def statements(self,actor,date_from=None,date_to=None,cost_center=None,source_module=None):
        conditions=[JournalEntry.branch_id==actor.branch_id,JournalEntry.posting_applied_at.is_not(None)]
        if date_to:conditions.append(JournalEntry.journal_date<=date_to)
        if cost_center:conditions.append(JournalEntryLine.cost_center==cost_center)
        if source_module:conditions.append(JournalEntry.source_module==source_module)
        grouped=select(Account.id,Account.account_code,Account.name,Account.category,Account.normal_balance,func.coalesce(func.sum(JournalEntryLine.debit_amount),0),func.coalesce(func.sum(JournalEntryLine.credit_amount),0)).join(JournalEntryLine,JournalEntryLine.account_id==Account.id).join(JournalEntry,JournalEntry.id==JournalEntryLine.journal_entry_id).where(*conditions).group_by(Account.id).order_by(Account.account_code,Account.id)
        cumulative=[];movement=[]
        for account_id,code,name,category,normal,debit,credit in self.db.execute(grouped):
            cumulative.append({'account_id':str(account_id),'code':code,'name':name,'category':category,'debit':str(max(Decimal(0),debit-credit)),'credit':str(max(Decimal(0),credit-debit)),'gross_debit_movements':str(debit),'gross_credit_movements':str(credit),'signed_balance':str(debit-credit)})
        if date_from:grouped=grouped.where(JournalEntry.journal_date>=date_from)
        grouped=grouped.where(or_(JournalEntry.source_module.is_(None),JournalEntry.source_module!='year_end_close'))
        for account_id,code,name,category,normal,debit,credit in self.db.execute(grouped):
            movement.append({'account_id':str(account_id),'code':code,'name':name,'category':category,'debit':str(debit),'credit':str(credit),'signed_balance':str(debit-credit)})
        income=-sum((Decimal(row['signed_balance']) for row in movement if row['category'] in {'income','revenue'}),Decimal(0))
        expenses=sum((Decimal(row['signed_balance']) for row in movement if row['category'] in {'expenses','expense'}),Decimal(0))
        assets=sum((Decimal(row['signed_balance']) for row in cumulative if row['category'] in {'assets','asset'}),Decimal(0))
        liabilities=-sum((Decimal(row['signed_balance']) for row in cumulative if row['category'] in {'liabilities','liability'}),Decimal(0))
        equity=-sum((Decimal(row['signed_balance']) for row in cumulative if row['category']=='equity'),Decimal(0))
        earnings=-sum((Decimal(row['signed_balance']) for row in cumulative if row['category'] in {'income','revenue','expenses','expense'}),Decimal(0))
        cash_flow=self.cash_flow(actor,date_from,date_to)
        from app.modules.accounting.controls import policy_for
        from app.utils.accounting_time import today_local
        policy=policy_for(self.db,actor.branch_id,date_to or today_local())
        settings=policy.settings if policy else {}
        company={key:settings.get(key,'') for key in ['legal_name','registration_number','tin','bin']}
        company.update({'branch_id':str(actor.branch_id),'policy_version':policy.version if policy else 0})
        return {'company':company,'cash_flow':cash_flow,'currency':'BDT','date_from':date_from,'date_to':date_to,'trial_balance':cumulative,'period_movements':movement,'total_debit':str(sum((Decimal(r['debit']) for r in cumulative),Decimal(0))),'total_credit':str(sum((Decimal(r['credit']) for r in cumulative),Decimal(0))),'profit_and_loss':{'income':str(income),'expenses':str(expenses),'net_profit':str(income-expenses)},'balance_sheet':{'assets':str(assets),'liabilities':str(liabilities),'equity':str(equity),'unclosed_earnings':str(earnings),'equation_difference':str(assets-liabilities-equity-earnings)}}

    def year_end(self,identity,actor,reason):
        lock_branch(self.db,actor)
        period=self.db.scalar(select(FinancialPeriod).where(FinancialPeriod.id==identity,FinancialPeriod.branch_id==actor.branch_id).with_for_update())
        if not period:raise AppException(404,'period_not_found','Financial period not found')
        from app.modules.accounting.service import AccountingService
        service=AccountingService(self.db)
        if service._source_entry_exists(actor.branch_id,'year_end_close',str(period.id)):return period
        if period.status!='open':raise AppException(409,'period_locked','Year-end adjustment requires an open period')
        pending=self.db.scalar(select(JournalEntry.id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.journal_date>=period.start_date,JournalEntry.journal_date<=period.end_date,JournalEntry.status.in_(['draft','submitted','approved'])).limit(1))
        if pending:raise AppException(409,'period_pending_vouchers','Resolve pending vouchers before year-end closing')
        book=self.statements(actor,period.start_date,period.end_date)
        lines=[]
        for row in book['period_movements']:
            if row['category'] not in {'income','revenue','expenses','expense'}:continue
            balance=Decimal(row['signed_balance'])
            if balance>0:lines.append((row['code'],row['name'],Decimal(0),balance))
            if balance<0:lines.append((row['code'],row['name'],-balance,Decimal(0)))
        net=sum((debit-credit for _,_,debit,credit in lines),Decimal(0))
        if net>0:lines.append(('3200','Retained Earnings',0,net))
        if net<0:lines.append(('3200','Retained Earnings',-net,0))
        if lines:service._create_auto_entry(actor,'year_end_close',str(period.id),period.end_date,'Approved year-end closing: '+reason,lines)
        self.db.flush();period.status='closed';period.updated_by=actor.id
        self.audit(actor,'accounting.year_end_close',period.id,{'reason':reason,'net_profit':str(net),'carry_forward':'Existing asset/liability/equity balances remain in the perpetual GL; no duplicate opening posting'})
        self.db.commit();return period

    def cash_flow(self,actor,date_from=None,date_to=None):
        from app.modules.accounting.controls import policy_for
        from app.utils.accounting_time import today_local
        policy=policy_for(self.db,actor.branch_id,date_to or today_local())
        settings=policy.settings if policy else {}
        codes=settings.get('cash_accounts',['1001','1011','1012','1013','1020'])
        mappings=settings.get('cash_flow_sources',{})
        conditions=[JournalEntry.branch_id==actor.branch_id,JournalEntry.posting_applied_at.is_not(None),JournalEntryLine.account_code.in_(codes)]
        if date_to:conditions.append(JournalEntry.journal_date<=date_to)
        grouped=select(JournalEntry.id,JournalEntry.source_module,JournalEntry.journal_date,JournalEntry.voucher_type,func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount)).join(JournalEntryLine,JournalEntryLine.journal_entry_id==JournalEntry.id).where(*conditions).group_by(JournalEntry.id)
        from app.models.accounting import SupplierPayment,SupplierInvoice
        capital_payments=set(self.db.scalars(select(JournalEntry.id).join(SupplierPayment,and_(SupplierPayment.payment_number==JournalEntry.source_reference,SupplierPayment.branch_id==JournalEntry.branch_id)).join(SupplierInvoice,SupplierInvoice.id==SupplierPayment.supplier_invoice_id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.source_module=='supplier_payment',SupplierInvoice.purchase_account_code=='1500')))
        opening=Decimal(0);buckets={'operating':Decimal(0),'investing':Decimal(0),'financing':Decimal(0),'opening_vouchers':Decimal(0),'unclassified':Decimal(0)}
        for identity,source,on,voucher,movement in self.db.execute(grouped):
            if date_from and on<date_from:opening+=movement;continue
            classification='opening_vouchers' if voucher=='opening' else mappings.get(source,'unclassified')
            if identity in capital_payments:classification='investing'
            if classification not in buckets:classification='unclassified'
            buckets[classification]+=movement
        change=sum(buckets.values(),Decimal(0))
        return {'opening_balance':str(opening),'movements':{key:str(value) for key,value in buckets.items()},'net_change':str(change),'closing_balance':str(opening+change),'basis':'Posted cash/bank movements. Clearing balances are excluded until settled; unclassified flows require accountant classification.'}

    def integrity(self,actor):
        from sqlalchemy import case
        query=select(JournalEntry.id,JournalEntry.journal_number,JournalEntry.total_debit,JournalEntry.total_credit,func.count(JournalEntryLine.id),func.coalesce(func.sum(JournalEntryLine.debit_amount),0),func.coalesce(func.sum(JournalEntryLine.credit_amount),0),func.sum(case((JournalEntryLine.account_id.is_(None),1),else_=0))).outerjoin(JournalEntryLine,JournalEntryLine.journal_entry_id==JournalEntry.id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.posting_applied_at.is_not(None)).group_by(JournalEntry.id)
        invalid=[]
        for identity,number,header_d,header_c,count,debit,credit,unmapped in self.db.execute(query):
            if count<2 or debit<=0 or debit!=credit or debit!=header_d or credit!=header_c or unmapped:invalid.append({'id':str(identity),'reference':number,'debit':str(debit),'credit':str(credit),'unmapped_lines':unmapped})
        duplicates=[{'account_code':code,'count':count} for code,count in self.db.execute(select(Account.account_code,func.count(Account.id)).where(Account.branch_id==actor.branch_id).group_by(Account.account_code).having(func.count(Account.id)>1))]
        signed=dict(self.db.execute(select(JournalEntryLine.account_id,func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount)).join(JournalEntry,JournalEntry.id==JournalEntryLine.journal_entry_id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.posting_applied_at.is_not(None)).group_by(JournalEntryLine.account_id)).all())
        cache=[]
        for account in self.db.scalars(select(Account).where(Account.branch_id==actor.branch_id)):
            book=signed.get(account.id,Decimal(0));book=-book if account.normal_balance=='credit' else book
            if book!=account.current_balance:cache.append({'account_code':account.account_code,'cached':str(account.current_balance),'posted_gl':str(book),'difference':str(account.current_balance-book)})
        from app.models.accounting import AccountingJournal,AccountingAuditLog
        mapped=set(self.db.scalars(select(AccountingAuditLog.entity_id).where(AccountingAuditLog.branch_id==actor.branch_id,AccountingAuditLog.action=='accounting.legacy_journal.resolve')))
        legacy=sum(1 for identity in self.db.scalars(select(AccountingJournal.id).where(AccountingJournal.branch_id==actor.branch_id)) if str(identity) not in mapped)
        return {'invalid_posted_journals':invalid,'duplicate_legacy_account_codes':duplicates,'opening_or_cache_differences':cache,'legacy_summary_journals_requiring_mapping':legacy,'can_close':not invalid and not cache and not duplicates and not legacy,'action':'Preserve original history. Use reviewed opening vouchers or approved correcting entries; do not silently repost legacy summary journals.'}

    def resolve_legacy_journal(self,identity,payload,actor):
        from app.models.accounting import AccountingJournal,AccountingAuditLog
        lock_branch(self.db,actor)
        original=self.db.scalar(select(AccountingJournal).where(AccountingJournal.id==identity,AccountingJournal.branch_id==actor.branch_id).with_for_update())
        entry=self.db.scalar(select(JournalEntry).where(JournalEntry.id==payload.journal_id,JournalEntry.branch_id==actor.branch_id,JournalEntry.status=='posted'))
        if not original or not entry:raise AppException(404,'legacy_resolution_source','Choose an original legacy summary and a posted branch voucher')
        previous=self.db.scalar(select(AccountingAuditLog.id).where(AccountingAuditLog.branch_id==actor.branch_id,AccountingAuditLog.action=='accounting.legacy_journal.resolve',AccountingAuditLog.entity_id==str(original.id)))
        if previous:raise AppException(409,'legacy_already_resolved','Legacy summary already has an immutable reconciliation decision')
        if payload.treatment=='already_posted' and (entry.total_debit!=original.debit_amount or entry.total_credit!=original.credit_amount):raise AppException(422,'legacy_resolution_amount','An already-posted match must have the same debit and credit totals')
        if payload.treatment=='included_in_opening' and entry.voucher_type!='opening':raise AppException(422,'legacy_opening_voucher','Choose the approved opening voucher incorporating this legacy balance')
        from app.modules.accounting.service import AccountingService
        AccountingService(self.db)._audit(actor,'accounting.legacy_journal.resolve','accounting_journal',str(original.id),{}, {'journal_id':str(entry.id),'journal_number':entry.journal_number,'treatment':payload.treatment,'reason':payload.reason,'original_debit':str(original.debit_amount),'original_credit':str(original.credit_amount),'cash_created':'0.00'})
        self.db.commit();return {'legacy_id':str(original.id),'journal_id':str(entry.id),'cash_created':'0.00'}
