"""Explicit approved statutory vouchers. No assumed Bangladesh tax rates or exemptions."""
from decimal import Decimal,ROUND_HALF_UP
from app.core.exceptions import AppException
from app.modules.accounting.controls import policy_for
from app.modules.accounting.service import AccountingService
from app.schemas.accounting import JournalEntryCreate,JournalEntryLineCreate
from app.schemas.accounting_standard import TaxRule


def statutory_voucher(db,payload,actor):
    policy=policy_for(db,actor.branch_id,payload.transaction_date)
    if not policy:raise AppException(422,'tax_policy_required','Approve an effective accounting policy with reviewed statutory rules')
    rules=[TaxRule.model_validate(rule) for rule in policy.settings.get('tax_rules',[]) if rule['code']==payload.tax_code and rule['service_category']==payload.service_category and rule['effective_from']<=payload.transaction_date.isoformat() and (not rule.get('effective_to') or rule['effective_to']>=payload.transaction_date.isoformat())]
    if len(rules)!=1:raise AppException(422,'tax_rule_not_found','Choose exactly one approved rule applicable to this category and date')
    rule=rules[0];rate=Decimal(0) if rule.exempt else rule.rate
    q=lambda value:value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    base=q(payload.basis_amount/(1+rate/100)) if rule.inclusive and rule.kind!='withholding' else q(payload.basis_amount)
    tax=q(payload.basis_amount-base) if rule.inclusive and rule.kind!='withholding' else q(base*rate/100)
    gross=base if rule.kind=='withholding' else base+tax
    line=lambda code,d=0,c=0:JournalEntryLineCreate(account_code=code,account_name=code,debit_amount=d,credit_amount=c)
    if rule.kind=='output_vat':lines=[line(payload.counterpart_account,gross),line(payload.base_account,c=base)]+([line(rule.ledger_account,c=tax)] if tax else [])
    elif rule.kind=='input_vat':lines=[line(payload.base_account,base),line(payload.counterpart_account,c=gross)]+([line(rule.ledger_account,tax)] if tax else [])
    else:lines=[line(payload.base_account,base),line(payload.counterpart_account,c=base-tax)]+([line(rule.ledger_account,c=tax)] if tax else [])
    lines=[item for item in lines if item.debit_amount or item.credit_amount]
    entry=AccountingService(db).create_journal_entry(JournalEntryCreate(journal_date=payload.transaction_date,narration='Reviewed tax '+rule.code+' / '+payload.document_reference,source_module='statutory_tax',source_reference=rule.code+':'+payload.request_key,request_key=payload.request_key,voucher_type='adjustment',status='draft' if policy.settings.get('maker_checker') else 'posted',lines=lines),actor,{})
    return {'journal_id':entry.id,'status':entry.status,'base':str(base),'tax':str(tax),'gross':str(gross),'tax_rule':rule.model_dump(mode='json'),'policy_version':policy.version}
