"""Atomic posting helpers. Callers validate the actor/source and own the transaction."""
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from app.core.exceptions import AppException
from app.models.branch import Branch
from app.models.operational_posting import OperationalPosting
from app.models.accounting import Account

ZERO=Decimal('0')
ACCOUNTS={'2450':('Vehicle Expense Payable','liabilities','credit'),'5300':('Vehicle Fuel Expense','expenses','debit'),'5310':('Vehicle Maintenance Expense','expenses','debit'),'2400':('Goods Received Clearing','liabilities','credit'),'4000':('Hospital Revenue','income','credit'),'1001':('Cash / Bank','assets','debit'),'1100':('Patient Receivable','assets','debit'),'1150':('Staff Meal Receivable','assets','debit'),'1300':('Inventory / Supplies','assets','debit'),'2200':('Payroll Payable','liabilities','credit'),'2300':('Payroll Deductions Clearing','liabilities','credit'),'4300':('Catering Revenue','income','credit'),'4400':('Transport Revenue','income','credit'),'5100':('Salary Expense','expenses','debit'),'5200':('Kitchen Consumption','expenses','debit'),'4100':('Refunds and Adjustments','expenses','debit')}

def lock_branch(db, actor):
    if not actor.branch_id or not db.scalar(select(Branch).where(Branch.id==actor.branch_id).with_for_update()):
        raise AppException(422,'posting_branch_required','Choose a hospital branch before posting')

def posted(db,kind,identity,event):
    return db.scalar(select(OperationalPosting).where(OperationalPosting.source_type==kind,OperationalPosting.source_id==identity,OperationalPosting.event==event))

def journal(db,actor,kind,identity,event,lines,*,invoice_id=None,details=None):
    lock_branch(db,actor)
    existing=posted(db,kind,identity,event)
    if existing:return existing
    amount=sum((Decimal(debit) for code,debit,credit in lines),ZERO).quantize(Decimal('.01'))
    if amount<=0:return None
    from app.modules.accounting.service import AccountingService
    normalized=[]
    for code,debit,credit in lines:
        name,category,normal=ACCOUNTS[code]
        account=db.scalar(select(Account).where(Account.branch_id==actor.branch_id,Account.account_code==code).with_for_update())
        if not account:
            account=Account(branch_id=actor.branch_id,account_code=code,name=name,category=category,normal_balance=normal,current_balance=0,opening_balance=0,created_by=actor.id,updated_by=actor.id)
            db.add(account);db.flush()
        normalized.append((code,account.name,Decimal(debit).quantize(Decimal(".01")),Decimal(credit).quantize(Decimal(".01"))))
    entry=AccountingService(db)._create_auto_entry(actor,kind,str(identity)+':'+event,date.today(),f'{kind} {event}: {identity}',normalized)
    entry.approved_by_user_id=None  # Derived source posting, not a separate human GL approval.
    db.flush()
    record=OperationalPosting(branch_id=actor.branch_id,source_type=kind,source_id=identity,event=event,amount=amount,invoice_id=invoice_id,journal_id=entry.id,details={**(details or {}),'policy':'operational_v1','source_actor_id':str(actor.id)},created_by=actor.id,updated_by=actor.id)
    db.add(record);db.flush();return record

def patient_charge(db,actor,kind,source,patient_id,amount,label,context,admission_id=None):
    amount=Decimal(amount).quantize(Decimal('.01'))
    if amount<=0 or source.posting_policy!='automatic':return None
    lock_branch(db,actor)
    if source.billing_invoice_id:return source.billing_invoice_id
    from app.models.billing import BillingItemConfig, BillingType
    from app.modules.billing.service import BillingServiceManager
    from app.schemas.billing import BillingInvoiceCreate,BillingInvoiceItemCreate
    billing_type=db.scalar(select(BillingType).where(BillingType.branch_id==actor.branch_id,BillingType.code==kind.upper()))
    if not billing_type:
        billing_type=BillingType(branch_id=actor.branch_id,code=kind.upper(),name=kind.title(),department=kind.title(),created_by=actor.id,updated_by=actor.id)
        db.add(billing_type);db.flush()
    if not billing_type.is_active:raise AppException(409,'support_billing_type_inactive','Enable the source billing classification before posting billable services')
    config=BillingItemConfig(id=uuid4(),branch_id=actor.branch_id,billing_type_id=billing_type.id,source_module=kind,source_entity_id=source.id,service_code=kind.upper()+'-'+source.id.hex,service_name=label[:180],unit_price=amount,created_by=actor.id,updated_by=actor.id)
    db.add(config);db.flush()
    invoice=BillingServiceManager(db).create_invoice(BillingInvoiceCreate(patient_id=patient_id,billing_type_id=billing_type.id,source_ipd_admission_id=admission_id,source_module=kind,billing_stage='ipd_interim' if admission_id else 'support_charge',note=label,items=[BillingInvoiceItemCreate(billing_service_id=config.id,quantity=1,source_module=kind,source_record_type=kind,source_record_id=source.id)]),actor,context,commit=False)
    source.billing_invoice_id=invoice.id
    journal(db,actor,kind,source.id,'invoice',[('1100',amount,ZERO),('4300' if kind=='catering' else '4400',ZERO,amount)],invoice_id=invoice.id)
    return invoice.id

def consume_meal_stock(db,actor,task):
    if task.posting_policy!='automatic':return
    from app.models.catering import CateringInventoryUsage
    from app.models.inventory import InventoryItem,InventoryStore,StockBatch,StockIssue
    from app.modules.inventory.service import InventoryService
    usages=list(db.scalars(select(CateringInventoryUsage).where(CateringInventoryUsage.meal_task_id==task.id).order_by(CateringInventoryUsage.inventory_item_id).with_for_update()))
    for usage in usages:
        if usage.stock_transaction_id:continue
        quantity=Decimal(usage.quantity_used)
        if quantity<=0:continue
        service=InventoryService(db)
        item=service._get_item_for_update(str(usage.inventory_item_id))
        store=db.scalar(select(InventoryStore).where(InventoryStore.id==usage.inventory_store_id,InventoryStore.branch_id==actor.branch_id,InventoryStore.is_active.is_(True)).with_for_update())
        if not store or item.branch_id!=actor.branch_id:
            raise AppException(422,'meal_stock_mapping','Configure a valid branch kitchen store and item before preparation')
        remaining=quantity;cost=ZERO;first_transaction=None
        while remaining>0:
            batch=service._get_item_batch_for_issue(item,store_id=str(store.id))
            if item.is_batch_tracked and not batch:
                raise AppException(409,'meal_stock_shortage','No usable kitchen stock batch; receive stock before preparation')
            used=min(remaining,Decimal(batch.quantity)) if batch else remaining
            unit_cost=Decimal(batch.unit_cost) if batch else (Decimal(item.stock_value)/Decimal(item.stock_quantity) if item.stock_quantity else ZERO)
            issue=StockIssue(id=uuid4(),item_id=item.id,store_id=store.id,batch_id=batch.id if batch else None,quantity=used,issue_date=date.today(),department='Kitchen',purpose='Meal preparation '+task.meal_number,patient_id=task.patient_id,created_by=actor.id,updated_by=actor.id)
            db.add(issue);db.flush()
            transaction=service._change_store_stock(store=store,item=item,delta=-used,actor=actor,movement_type='issue',reference_type='catering_meal',reference_id=task.id,batch=batch,note='Consumed for '+task.meal_number,unit_cost=unit_cost)
            if batch:batch.quantity=Decimal(batch.quantity)-used
            db.flush();first_transaction=first_transaction or transaction.id;cost+=used*unit_cost;remaining-=used
        usage.stock_transaction_id=first_transaction;usage.stock_status='consumed'
        journal(db,actor,'catering_stock',usage.id,'consume',[('5200',cost,ZERO),('1300',ZERO,cost)],details={'quantity':str(quantity),'meal_id':str(task.id),'store_id':str(store.id)})
    if usages:task.inventory_status='consumed'

def billing_cash_event(db,actor,invoice,record,kind):
    # Only invoices originated by this automatic pipeline are enrolled.
    if not db.scalar(select(OperationalPosting.id).where(OperationalPosting.invoice_id==invoice.id,OperationalPosting.event=='invoice')):return
    amount=Decimal(record.amount)
    if kind=='billing_payment':
        journal(db,actor,kind,record.id,'receipt',[('1001',amount,ZERO),('1100',ZERO,amount)],invoice_id=invoice.id)
        # Accounting's existing source sync recognizes the receipt and cannot duplicate it.
    elif kind=='billing_return':
        credit=Decimal(record.credit_amount)
        journal(db,actor,kind,record.id,'credit',[('4100',credit,ZERO),('1100',ZERO,credit)],invoice_id=invoice.id)
        if amount:journal(db,actor,'billing_refund',record.id,'payout',[('1100',amount,ZERO),('1001',ZERO,amount)],invoice_id=invoice.id)
    else:
        journal(db,actor,'billing_refund',record.id,'payout',[('1100',amount,ZERO),('1001',ZERO,amount)],invoice_id=invoice.id)
    from app.models.transport import TransportTrip
    for source in db.scalars(select(OperationalPosting).where(OperationalPosting.invoice_id==invoice.id,OperationalPosting.source_type=='transport',OperationalPosting.event=='invoice')):
        trip=db.get(TransportTrip,source.source_id)
        if trip:
            trip.billing_status=invoice.payment_status
            if trip.request:trip.request.billing_status=invoice.payment_status
    from app.models.accounting import JournalEntry
    for post in db.scalars(select(OperationalPosting).where(OperationalPosting.source_id==record.id,OperationalPosting.journal_id.is_not(None))):
        entry=db.get(JournalEntry,post.journal_id)
        if entry and entry.source_module in {'billing_payment','billing_refund'}:entry.source_reference=getattr(record,'receipt_number',None) or record.refund_number

def posting_rows(db,actor,kinds):
    rows=db.scalars(select(OperationalPosting).where(OperationalPosting.branch_id==actor.branch_id,OperationalPosting.source_type.in_(kinds)).order_by(OperationalPosting.created_at.desc()).limit(200))
    return [{column.name:getattr(row,column.name) for column in row.__table__.columns} for row in rows]

def enroll_invoice(db,actor,invoice,carried):
    """Accrue new charges once; final bills reuse the receivable already accrued."""
    if invoice.source_module in {'catering','transport'}:return
    lock_branch(db,actor)
    legacy=[row for row in carried.values() if not db.scalar(select(OperationalPosting.id).where(OperationalPosting.invoice_id==row['prior'].invoice_id,OperationalPosting.event=='invoice'))]
    if legacy:
        db.add(OperationalPosting(branch_id=actor.branch_id,source_type='billing_invoice',source_id=invoice.id,event='review_required',amount=0,invoice_id=invoice.id,details={'reason':'Carried legacy invoices have no verified accrual; reconcile before automatic accounting'},created_by=actor.id,updated_by=actor.id));return
    amount=Decimal(invoice.total_amount)-sum((row['net'] for row in carried.values()),ZERO)
    record=journal(db,actor,'billing_invoice',invoice.id,'invoice',[('1100',amount,ZERO),('4000',ZERO,amount)],invoice_id=invoice.id,details={'carried_total':str(sum((row['net'] for row in carried.values()),ZERO))})
    if not record:
        db.add(OperationalPosting(branch_id=actor.branch_id,source_type='billing_invoice',source_id=invoice.id,event='invoice',amount=0,invoice_id=invoice.id,details={'carried_total':str(invoice.total_amount)},created_by=actor.id,updated_by=actor.id))

def amend_invoice_posting(db,actor,invoice,before):
    if not db.scalar(select(OperationalPosting.id).where(OperationalPosting.invoice_id==invoice.id,OperationalPosting.event=='invoice')):return
    delta=Decimal(str(before['total_amount']))-Decimal(invoice.total_amount)
    if not delta:return
    # Each accepted amendment is a new, immutable accounting source.
    reference=uuid4()
    lines=[('4100',delta,ZERO),('1100',ZERO,delta)] if delta>0 else [('1100',-delta,ZERO),('4000',ZERO,-delta)]
    journal(db,actor,'billing_amendment',reference,'discount',lines,invoice_id=invoice.id,details={'invoice_id':str(invoice.id),'before':str(before['total_amount']),'after':str(invoice.total_amount)})

def void_invoice_posting(db,actor,invoice):
    source=db.scalar(select(OperationalPosting).where(OperationalPosting.invoice_id==invoice.id,OperationalPosting.event=='invoice'))
    if not source:return
    if invoice.billing_stage=='ipd_final' and source.details and Decimal(source.details.get('carried_total','0'))>0:
        raise AppException(409,'final_invoice_reversal_review','A final bill carrying earlier charges requires a reviewed reversal; do not void its linked history')
    remaining=Decimal(invoice.total_amount)-sum((Decimal(refund.credit_amount) for refund in invoice.refunds),ZERO)
    journal(db,actor,'billing_invoice',invoice.id,'void',[('4100',remaining,ZERO),('1100',ZERO,remaining)],invoice_id=invoice.id)
