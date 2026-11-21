"""Accrual pharmacy sales and weighted-average stock cost, enabled by approved policy."""
from datetime import date
from app.utils.accounting_time import today_local
from decimal import Decimal,ROUND_HALF_UP
from app.core.exceptions import AppException
from app.modules.accounting.controls import policy_for
from app.modules.accounting.service import AccountingService


def enabled(db,actor,on_date=None):
    policy=policy_for(db,actor.branch_id,on_date or today_local())
    return bool(policy and policy.settings.get('pharmacy_accounting_enabled',True))


def value_movement(db,actor,medicine,delta,stock_before,unit_cost=None):
    if not enabled(db,actor):return unit_cost
    if medicine.inventory_value is None:
        if stock_before:raise AppException(409,'pharmacy_opening_valuation','Reconcile this medicine opening stock to a posted inventory opening voucher first')
        medicine.inventory_value=Decimal(0)
    if delta>0:
        if unit_cost is None:raise AppException(422,'pharmacy_cost_required','Incoming stock needs a verified purchase or original return cost')
        cost=Decimal(unit_cost)
    else:cost=Decimal(medicine.inventory_value)/stock_before if stock_before else Decimal(0)
    change=(Decimal(delta)*cost).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    if medicine.inventory_value+change<0:raise AppException(409,'pharmacy_inventory_value','Inventory value would become negative')
    medicine.inventory_value+=change
    return cost


def assert_unposted(db,actor,kind,reference):
    if AccountingService(db)._source_entry_exists(actor.branch_id,kind,reference):raise AppException(409,'pharmacy_posted_immutable','Posted pharmacy transactions require a return or approved financial adjustment')


def post_purchase(db,actor,purchase):
    if not enabled(db,actor,purchase.purchase_date):return
    if purchase.total_amount:AccountingService(db)._create_auto_entry(actor,'pharmacy_purchase',purchase.purchase_number,purchase.purchase_date,'Pharmacy inventory receipt / supplier liability '+purchase.purchase_number,[('1310','Pharmacy Inventory',purchase.total_amount,0),('2400','Goods Received Clearing',0,purchase.total_amount)])


def post_sale(db,actor,sale):
    if not enabled(db,actor,sale.sale_date):return
    if sale.paid_amount is None:raise AppException(422,'pharmacy_collection_required','Enter the amount actually received; zero records a credit sale')
    if sale.paid_amount>sale.net_payable:raise AppException(422,'pharmacy_payment_excess','Pharmacy collection exceeds the net sale')
    from app.modules.accounting.channels import collection_account
    lines=[]
    if sale.paid_amount:lines.append((collection_account(db,actor,sale.payment_method,sale.payment_provider,sale.sale_date),'Actual pharmacy collection',sale.paid_amount,0))
    due=sale.net_payable-sale.paid_amount
    if due:lines.append(('1100','Patient / customer receivable',due,0))
    if sale.net_payable:lines.append(('4200','Pharmacy Sales',0,sale.net_payable))
    cost=sum((item.cost_amount or Decimal(0) for item in sale.items),Decimal(0))
    if cost:lines += [('5030','Medicine Cost of Goods Sold',cost,0),('1310','Pharmacy Inventory',0,cost)]
    if lines:AccountingService(db)._create_auto_entry(actor,'pharmacy_sale',sale.sale_number,sale.sale_date,'Pharmacy sale and weighted-average cost '+sale.sale_number,lines)


def return_amount(db,actor,sale,sale_item,quantity):
    if not enabled(db,actor):return quantity*sale_item.unit_price
    from app.modules.billing.policies import allocate
    from app.utils.billing_amounts import money
    shares=allocate(sale.discount_amount,{item.id:item.line_total for item in sale.items if item.is_active})
    net=sale_item.line_total-shares[sale_item.id]
    before=sale_item.returned_quantity-quantity
    return money(net*sale_item.returned_quantity/sale_item.quantity)-money(net*before/sale_item.quantity)


def post_return(db,actor,sale,sale_item,record,original_paid):
    if not enabled(db,actor,record.returned_at):return
    from app.utils.billing_amounts import money
    original=sale.subtotal-sale.discount_amount
    previous_credit=sale.return_amount-record.total_amount
    due=max(Decimal(0),original-previous_credit-Decimal(original_paid or 0))
    ar=min(due,record.total_amount);refund=record.total_amount-ar
    lines=[('4200','Pharmacy sales return',record.total_amount,0)] if record.total_amount else []
    if ar:lines.append(('1100','Customer credit adjustment',0,ar))
    if refund:lines.append(('2220','Customer Refund Payable',0,refund))
    if sale_item.cost_amount is None:raise AppException(409,'pharmacy_return_cost','Original sale has no verified cost snapshot; reconcile the legacy return before accounting')
    before=sale_item.returned_quantity-record.quantity
    cost=money(sale_item.cost_amount*sale_item.returned_quantity/sale_item.quantity)-money(sale_item.cost_amount*before/sale_item.quantity)
    if cost:lines += [('1310','Returned Pharmacy Inventory',cost,0),('5030','Returned medicine cost',0,cost)]
    if lines:AccountingService(db)._create_auto_entry(actor,'pharmacy_return',record.return_number,record.returned_at,'Pharmacy return / refund payable '+record.return_number,lines)


def set_opening_value(db,identity,payload,actor):
    from sqlalchemy import select,func
    from app.models.pharmacy import PharmacyMedicine
    from app.models.accounting import JournalEntry
    from app.modules.support_posting.service import lock_branch
    from app.modules.accounting.management import AccountingManagement
    lock_branch(db,actor)
    medicine=db.scalar(select(PharmacyMedicine).where(PharmacyMedicine.id==identity,PharmacyMedicine.branch_id==actor.branch_id).with_for_update())
    if not medicine:raise AppException(404,'medicine_not_found','Branch medicine not found')
    if medicine.inventory_value is not None:raise AppException(409,'pharmacy_already_valued','Opening stock value is already established; use a reviewed adjustment')
    entry=db.scalar(select(JournalEntry).where(JournalEntry.id==payload.journal_id,JournalEntry.branch_id==actor.branch_id,JournalEntry.status=='posted').with_for_update())
    if not entry:raise AppException(422,'pharmacy_opening_journal','Choose a posted branch inventory opening voucher')
    available=sum((line.debit_amount-line.credit_amount for line in entry.lines if line.account_code=='1310'),Decimal(0))
    allocated=db.scalar(select(func.coalesce(func.sum(PharmacyMedicine.valuation_opening_value),0)).where(PharmacyMedicine.valuation_opening_journal_id==entry.id)) or Decimal(0)
    if payload.amount>available-allocated:raise AppException(422,'pharmacy_opening_amount','Value exceeds the unassigned inventory amount in this voucher')
    medicine.inventory_value=payload.amount;medicine.valuation_opening_value=payload.amount;medicine.valuation_opening_journal_id=entry.id;medicine.updated_by=actor.id
    AccountingManagement(db).audit(actor,'pharmacy.opening_valuation',medicine.id,{'amount':str(payload.amount),'stock_quantity':str(medicine.stock_quantity),'journal_id':str(entry.id),'reason':payload.reason});db.commit();return {'medicine_id':medicine.id,'inventory_value':str(medicine.inventory_value)}


def pay_return(db,identity,payload,actor):
    """Discharge only the original return's refund liability, once, with evidence."""
    from sqlalchemy import select
    from app.models.pharmacy import PharmacySaleReturn
    from app.models.accounting import JournalEntry
    from app.modules.support_posting.service import lock_branch
    from app.modules.accounting.channels import collection_account
    from app.modules.accounting.management import AccountingManagement
    lock_branch(db,actor)
    record=db.scalar(select(PharmacySaleReturn).where(PharmacySaleReturn.id==identity,PharmacySaleReturn.branch_id==actor.branch_id).with_for_update())
    if not record:raise AppException(404,'pharmacy_return_not_found','Branch return not found')
    snapshot=payload.model_dump(mode='json')
    previous=db.scalar(select(JournalEntry).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.source_module=='pharmacy_refund_payment',JournalEntry.source_reference==str(identity)))
    if previous:
        if (previous.policy_snapshot or {}).get('source')!=snapshot:raise AppException(409,'pharmacy_refund_conflict','Refund already paid with different payment information')
        return previous
    original=db.scalar(select(JournalEntry).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.source_module=='pharmacy_return',JournalEntry.source_reference==record.return_number,JournalEntry.status=='posted'))
    if not original:raise AppException(409,'pharmacy_refund_unposted','Reconcile this return to a verified posted liability before paying')
    payable=sum((line.credit_amount-line.debit_amount for line in original.lines if line.account_code=='2220'),Decimal(0))
    if payable<=0 or payload.amount!=payable:raise AppException(422,'pharmacy_refund_amount','Pay exactly this return’s outstanding refund liability; credit-only returns have no cash refund')
    policy=policy_for(db,actor.branch_id,today_local())
    if not policy:raise AppException(409,'pharmacy_refund_policy','Approve an accounting policy before paying refunds')
    if policy.settings.get('maker_checker',True) and actor.id==record.returned_by_user_id:raise AppException(403,'pharmacy_refund_self_approval','An independent authorized manager must disburse the refund')
    channel=collection_account(db,actor,payload.payment_method,payload.payment_provider)
    entry=AccountingService(db)._create_auto_entry(actor,'pharmacy_refund_payment',str(identity),today_local(),'Actual pharmacy refund '+record.return_number+' / '+payload.reference,[('2220','Discharged customer refund liability',payable,0),(channel,'Actual refund disbursement',0,payable)],source_snapshot=snapshot)
    AccountingManagement(db).audit(actor,'pharmacy.refund.pay',record.id,{'journal_id':str(entry.id),'reference':payload.reference,'amount':str(payable)})
    db.commit();return entry
