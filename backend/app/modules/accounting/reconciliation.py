"""Bank/MFS statement rows are external evidence, never automatically cash postings."""
import hashlib
from decimal import Decimal
from sqlalchemy import select
from app.core.exceptions import AppException
from app.models.accounting import Account,BankTransaction,JournalEntry
from app.modules.support_posting.service import lock_branch
from app.modules.accounting.management import AccountingManagement


class Reconciliation:
    def __init__(self,db):self.db=db
    def import_rows(self,payload,actor):
        lock_branch(self.db,actor)
        account=self.db.scalar(select(Account).where(Account.branch_id==actor.branch_id,Account.account_code==payload.ledger_account_code,Account.is_active.is_(True)))
        if not account or account.category!='assets' or account.is_control:raise AppException(422,'statement_account','Choose a branch bank / clearing asset account')
        inserted=duplicates=0
        for item in payload.rows:
            key=hashlib.sha256((payload.ledger_account_code+':'+item.external_id).encode()).hexdigest()
            prior=self.db.scalar(select(BankTransaction).where(BankTransaction.branch_id==actor.branch_id,BankTransaction.statement_key==key))
            direction='receipt' if item.signed_amount>0 else 'payment'
            if prior:
                if prior.amount!=abs(item.signed_amount) or prior.transaction_type!=direction or prior.transaction_date!=item.transaction_date or prior.reference_number!=item.reference:raise AppException(409,'statement_duplicate_conflict','External statement row ID was reused for different financial data')
                duplicates+=1;continue
            row=BankTransaction(branch_id=actor.branch_id,ledger_account_code=payload.ledger_account_code,statement_key=key,transaction_date=item.transaction_date,transaction_type=direction,reference_number=item.reference,amount=abs(item.signed_amount),reconciliation_status='unmatched',created_by=actor.id,updated_by=actor.id)
            self.db.add(row);self.db.flush();inserted+=1
        AccountingManagement(self.db).audit(actor,'bank_statement.import',account.id,{'inserted':inserted,'duplicates':duplicates});self.db.commit();return {'inserted':inserted,'duplicates':duplicates}
    def match(self,identity,payload,actor):
        lock_branch(self.db,actor)
        row=self.db.scalar(select(BankTransaction).where(BankTransaction.id==identity,BankTransaction.branch_id==actor.branch_id).with_for_update())
        if not row:raise AppException(404,'statement_not_found','Statement row not found')
        previous_journal=row.matched_journal_id
        if row.matched_journal_id:
            if row.matched_journal_id==payload.journal_id:return row
            previous=self.db.get(JournalEntry,row.matched_journal_id)
            if previous and previous.status=='posted':raise AppException(409,'statement_already_matched','Reverse an incorrect voucher before linking its approved replacement')
        entry=self.db.scalar(select(JournalEntry).where(JournalEntry.id==payload.journal_id,JournalEntry.branch_id==actor.branch_id,JournalEntry.status=='posted').with_for_update())
        if not entry:raise AppException(422,'statement_journal','Choose a posted journal in this branch')
        signed=row.amount if row.transaction_type=='receipt' else -row.amount
        movement=sum((line.debit_amount-line.credit_amount for line in entry.lines if line.account_code==row.ledger_account_code),Decimal(0))
        used=self.db.scalar(select(BankTransaction.id).where(BankTransaction.matched_journal_id==entry.id,BankTransaction.ledger_account_code==row.ledger_account_code,BankTransaction.id!=row.id))
        if used or movement!=signed:raise AppException(422,'statement_amount_mismatch','Voucher movement must match this unmatched account / amount exactly')
        row.matched_journal_id=entry.id;row.matched_reference=entry.journal_number;row.reconciliation_status='matched';row.updated_by=actor.id
        AccountingManagement(self.db).audit(actor,'bank_statement.match',row.id,{'previous_journal_id':str(previous_journal) if previous_journal else None,'journal_id':str(entry.id),'reason':payload.reason,'statement_amount':str(signed),'statement_date':row.transaction_date.isoformat(),'journal_date':entry.journal_date.isoformat()});self.db.commit();return row
    def rows(self,actor):
        result=[]
        for row in self.db.scalars(select(BankTransaction).where(BankTransaction.branch_id==actor.branch_id).order_by(BankTransaction.transaction_date.desc()).limit(500)):
            entry=self.db.get(JournalEntry,row.matched_journal_id) if row.matched_journal_id else None
            status='reversal_review' if entry and entry.status!='posted' else row.reconciliation_status
            result.append({**{column.name:getattr(row,column.name) for column in row.__table__.columns},'current_reconciliation_status':status})
        return result

    def suggestions(self,identity,actor,days=3):
        from datetime import timedelta
        from sqlalchemy import func
        from app.models.accounting import JournalEntryLine
        row=self.db.scalar(select(BankTransaction).where(BankTransaction.id==identity,BankTransaction.branch_id==actor.branch_id))
        if not row:raise AppException(404,'statement_not_found','Statement row not found')
        amount=row.amount if row.transaction_type=='receipt' else -row.amount
        dates=(row.transaction_date-timedelta(days=days),row.transaction_date+timedelta(days=days))
        query=select(JournalEntry.id,JournalEntry.journal_number,JournalEntry.journal_date,JournalEntry.source_reference,JournalEntry.narration).join(JournalEntryLine,JournalEntry.id==JournalEntryLine.journal_entry_id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.status=='posted',JournalEntry.journal_date>=dates[0],JournalEntry.journal_date<=dates[1],JournalEntryLine.account_code==row.ledger_account_code).group_by(JournalEntry.id).having(func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount)==amount).order_by(JournalEntry.journal_date.desc()).limit(20)
        used=set(self.db.scalars(select(BankTransaction.matched_journal_id).where(BankTransaction.branch_id==actor.branch_id,BankTransaction.ledger_account_code==row.ledger_account_code,BankTransaction.matched_journal_id.is_not(None))))
        return [{'id':identity,'journal_number':number,'journal_date':on,'reference':reference,'narration':description,'reference_match':bool(row.reference_number and row.reference_number in (reference or '')+' '+description)} for identity,number,on,reference,description in self.db.execute(query) if identity not in used]
