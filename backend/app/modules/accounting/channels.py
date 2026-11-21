"""Collection-channel mapping: clearing is kept separate from settled bank cash."""
from datetime import date
from app.utils.accounting_time import today_local
from app.core.exceptions import AppException
from app.modules.accounting.controls import policy_for

DEFAULT_CHANNELS={'patient_advance':'2210','cash':'1001','bank_transfer':'1020','bank':'1020','bkash':'1031','nagad':'1032','rocket':'1033','card':'1034'}


def collection_account(db,actor,method,provider=None,on_date=None):
    key=str(provider or method).lower().replace(' ','_')
    if method=='mobile_banking' and key not in {'bkash','nagad','rocket'}:
        raise AppException(422,'accounting_payment_channel','Configure a verified mobile payment provider before posting')
    policy=policy_for(db,actor.branch_id,on_date or today_local())
    mappings=policy.settings.get('collection_accounts',{}) if policy else {}
    code=mappings.get(key) or mappings.get(method) or DEFAULT_CHANNELS.get(key) or DEFAULT_CHANNELS.get(method)
    if not code:raise AppException(422,'accounting_payment_channel','Payment channel has no configured ledger account')
    from app.modules.accounting.coa import ensure_account
    return ensure_account(db,actor,code).account_code
