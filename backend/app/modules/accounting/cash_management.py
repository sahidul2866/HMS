"""Cashier counts and actual cash/bank/clearing transfers on the shared GL."""
from datetime import UTC,datetime
from decimal import Decimal
from sqlalchemy import select,func
from app.core.exceptions import AppException
from app.models.accounting import Account,CashClosing,JournalEntry,JournalEntryLine
from app.modules.support_posting.service import lock_branch
from app.modules.accounting.management import AccountingManagement


class CashManagement:
    def __init__(self,db):self.db=db

    def open_shift(self,payload,actor):
        lock_branch(self.db,actor)
        if self.db.scalar(select(CashClosing.id).where(CashClosing.branch_id==actor.branch_id,CashClosing.cashier_user_id==actor.id,CashClosing.status=='open')):
            raise AppException(409,'cash_shift_open','Close the existing shift before opening another')
        from app.modules.accounting.coa import ensure_account
        account=ensure_account(self.db,actor,payload.cash_account_code)
        if account.category!='assets' or account.is_control or not account.is_active:raise AppException(422,'cash_shift_account','Choose an active cash asset account')
        now=datetime.now(UTC)
        from app.modules.opd.dashboard import hospital_today
        row=CashClosing(branch_id=actor.branch_id,cashier_user_id=actor.id,closing_date=hospital_today(),cash_account_code=payload.cash_account_code,counter_name=payload.counter_name,opening_balance=payload.opening_balance,expected_cash=payload.opening_balance,status='open',opened_at=now,created_by=actor.id,updated_by=actor.id)
        self.db.add(row);self.db.flush();AccountingManagement(self.db).audit(actor,'cash_shift.open',row.id,{'opening_cash':str(payload.opening_balance),'account':account.account_code});self.db.commit();return row

    def close_shift(self,identity,payload,actor):
        lock_branch(self.db,actor)
        row=self.db.scalar(select(CashClosing).where(CashClosing.id==identity,CashClosing.branch_id==actor.branch_id,CashClosing.cashier_user_id==actor.id).with_for_update())
        if not row:raise AppException(404,'cash_shift_not_found','Your cashier shift was not found')
        if row.status!='open':raise AppException(409,'cash_shift_closed','This shift already has a frozen physical cash count')
        delta=self.db.scalar(select(func.coalesce(func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount),0)).join(JournalEntry,JournalEntry.id==JournalEntryLine.journal_entry_id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.created_by==actor.id,JournalEntry.posting_applied_at.is_not(None),JournalEntry.created_at>=row.opened_at,JournalEntryLine.account_code==row.cash_account_code)) or Decimal(0)
        row.expected_cash=row.opening_balance+delta;row.actual_cash=payload.counted_cash;row.difference_amount=row.actual_cash-row.expected_cash
        row.closed_at=datetime.now(UTC);row.status='pending';row.remarks=payload.note;row.updated_by=actor.id
        AccountingManagement(self.db).audit(actor,'cash_shift.count',row.id,{'expected':str(row.expected_cash),'counted':str(row.actual_cash),'difference':str(row.difference_amount),'note':payload.note});self.db.commit();return row

    def approve_shift(self,identity,actor,reason):
        lock_branch(self.db,actor)
        row=self.db.scalar(select(CashClosing).where(CashClosing.id==identity,CashClosing.branch_id==actor.branch_id).with_for_update())
        if not row:raise AppException(404,'cash_shift_not_found','Cashier shift not found')
        if row.status=='approved':return row
        if row.status!='pending':raise AppException(409,'cash_shift_state','Cashier must submit a physical count first')
        if row.cashier_user_id==actor.id:raise AppException(403,'cash_shift_self_approval','A supervisor must approve the cashier count and discrepancy')
        row.status='approved';row.approved_by_user_id=actor.id;row.updated_by=actor.id
        AccountingManagement(self.db).audit(actor,'cash_shift.approve',row.id,{'reason':reason,'discrepancy':str(row.difference_amount)});self.db.commit();return row

    def transfer(self,payload,actor):
        from app.modules.accounting.service import AccountingService
        from app.modules.accounting.controls import policy_for
        from app.schemas.accounting import JournalEntryCreate,JournalEntryLineCreate
        lock_branch(self.db,actor)
        accounts={row.account_code:row for row in self.db.scalars(select(Account).where(Account.branch_id==actor.branch_id,Account.account_code.in_([payload.from_account,payload.to_account])))}
        if len(accounts)!=2 or any(row.category!='assets' or row.is_control or not row.is_active for row in accounts.values()):raise AppException(422,'transfer_account','Choose two active branch asset accounts')
        policy=policy_for(self.db,actor.branch_id,payload.transaction_date)
        lines=[JournalEntryLineCreate(account_code=payload.from_account,account_name=accounts[payload.from_account].name,credit_amount=payload.amount),JournalEntryLineCreate(account_code=payload.to_account,account_name=accounts[payload.to_account].name,debit_amount=payload.amount-payload.processing_charge)]
        if payload.processing_charge:lines.append(JournalEntryLineCreate(account_code=payload.charge_account,account_name='Configured processing charges',debit_amount=payload.processing_charge))
        return AccountingService(self.db).create_journal_entry(JournalEntryCreate(journal_date=payload.transaction_date,narration='Cash / bank / clearing transfer: '+payload.reference,source_module='cash_transfer',source_reference=payload.request_key,request_key=payload.request_key,voucher_type='contra',status='draft' if policy and policy.settings.get('maker_checker') else 'posted',lines=lines),actor,{})
