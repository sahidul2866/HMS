"""Shared validation for manual and all automatic GL postings."""
from datetime import UTC, datetime
from decimal import Decimal
import hashlib,json
from sqlalchemy import select,cast,String
from app.core.exceptions import AppException
from app.models.accounting import JournalEntry
from app.models.accounting_control import AccountingPolicy,FinancialPeriod,AccountingPostingKey


def policy_for(db,branch_id,on_date):
    return db.scalar(select(AccountingPolicy).where(AccountingPolicy.branch_id==branch_id,AccountingPolicy.effective_from<=on_date,AccountingPolicy.approved_by.is_not(None)).order_by(AccountingPolicy.effective_from.desc(),AccountingPolicy.version.desc()).limit(1))


def validate_posting(db,entry,actor):
    from app.modules.support_posting.service import lock_branch
    lock_branch(db,actor)
    if entry.branch_id!=actor.branch_id:raise AppException(403,'accounting_branch','Posting must remain in the active branch')
    if entry.posting_applied_at:raise AppException(409,'journal_already_posted','This journal has already affected the ledger')
    if len(entry.lines)<2:raise AppException(422,'journal_lines','At least two journal lines are required')
    debit=credit=Decimal(0)
    for line in entry.lines:
        d,c=Decimal(line.debit_amount or 0),Decimal(line.credit_amount or 0)
        if not d.is_finite() or not c.is_finite() or d<0 or c<0 or (d>0)==(c>0) or d!=d.quantize(Decimal('.01')) or c!=c.quantize(Decimal('.01')):
            raise AppException(422,'journal_line_amount','Each line needs one nonnegative, two-decimal debit or credit')
        debit+=d;credit+=c
    if debit>Decimal('999999999999.99'):raise AppException(422,'journal_amount_limit','Voucher total exceeds the supported ledger precision')
    if debit<=0 or debit!=credit or debit!=entry.total_debit or credit!=entry.total_credit:
        raise AppException(422,'unbalanced_voucher','Line debits and credits must equal each other and the voucher totals')
    policy=policy_for(db,entry.branch_id,entry.journal_date)
    settings=policy.settings if policy else {}
    if settings and entry.voucher_type!='opening':
        from app.models.accounting import AccountingJournal,AccountingAuditLog
        resolved=select(AccountingAuditLog.id).where(AccountingAuditLog.branch_id==entry.branch_id,AccountingAuditLog.action=='accounting.legacy_journal.resolve',AccountingAuditLog.entity_id==cast(AccountingJournal.id,String)).exists()
        if db.scalar(select(AccountingJournal.id).where(AccountingJournal.branch_id==entry.branch_id,~resolved).limit(1)):raise AppException(409,'accounting_legacy_cutover','Resolve legacy summary journals against reviewed opening or already-posted vouchers before new financial postings')
    if settings.get('cutover_date') and entry.journal_date.isoformat()<settings['cutover_date']:
        raise AppException(409,'accounting_before_cutover','Use reviewed opening balances for pre-cutover transactions')
    periods=list(db.scalars(select(FinancialPeriod).where(FinancialPeriod.branch_id==actor.branch_id,FinancialPeriod.start_date<=entry.journal_date,FinancialPeriod.end_date>=entry.journal_date).with_for_update()))
    if len(periods)>1:raise AppException(409,'accounting_period_overlap','Financial periods overlap; resolve configuration')
    if periods and periods[0].status!='open':raise AppException(409,'accounting_period_locked','Post an approved adjustment in an open period')
    if not periods and settings.get('period_required'):raise AppException(422,'accounting_period_required','Configure an open financial period first')
    entry.period_id=periods[0].id if periods else None
    source=(entry.policy_snapshot or {}).get('source')
    entry.policy_snapshot={'version':policy.version,'settings':settings} if policy else {'version':0,'legacy_compatibility':True}
    if source:entry.policy_snapshot={**entry.policy_snapshot,'source':source}
    if entry.source_module and entry.source_reference:
        representation={'date':entry.journal_date.isoformat(),'lines':[(line.account_code,str(line.debit_amount or 0),str(line.credit_amount or 0),line.cost_center) for line in entry.lines]}
        digest=hashlib.sha256(json.dumps(representation,sort_keys=True).encode()).hexdigest()
        previous=db.scalar(select(AccountingPostingKey).where(AccountingPostingKey.branch_id==actor.branch_id,AccountingPostingKey.source_module==entry.source_module,AccountingPostingKey.source_reference==entry.source_reference))
        if previous:raise AppException(409,'duplicate_accounting_source','This source event already has a journal; use an adjustment or reversal')
        db.add(AccountingPostingKey(branch_id=actor.branch_id,source_module=entry.source_module,source_reference=entry.source_reference,journal=entry,fingerprint=digest,created_by=actor.id,updated_by=actor.id))
    return settings


SYSTEM_SOURCES={'billing_invoice','billing_payment','billing_return','billing_refund','billing_amendment','billing_allocation','doctor_direct_collection','patient_advance','payment_adjustment','supplier_invoice','supplier_payment','expense_accrual','expense_payment','pharmacy_purchase','pharmacy_sale','pharmacy_return','pharmacy_refund_payment','pharmacy_dispense_cost','inventory_receiving','inventory_cost','hr_payroll','asset_depreciation','asset_disposal','year_end_close','manual_request','employee_advance_disbursement'}
