"""Reverse only an inspected, identified original issue; unfit goods stay out of stock."""
from datetime import UTC, datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select
from app.core.exceptions import AppException
from app.models.pharmacy import PharmacyDispense, PharmacyStockMovement, PharmacyMedicine
from app.models.inventory import InventoryStockTransaction, InventoryItem, InventoryStoreItem, StockBatch


def sources(db, dispense):
    used={}
    for entry in dispense.return_history or []:
        key=entry['source_issue_id'];used[key]=used.get(key,Decimal(0))+Decimal(entry['quantity'])
    records=[]
    for model,kind,ref in [(InventoryStockTransaction,'inventory','pharmacy_dispense'),(PharmacyStockMovement,'pharmacy','dispense')]:
        for issue in db.scalars(select(model).where(model.reference_id==dispense.id,model.reference_type==ref,model.quantity_change<0)):
            batch=issue.batch if kind=='inventory' else None
            records.append({'id':str(issue.id),'kind':kind,'batch_no':batch.batch_no if batch else getattr(issue,'batch_no',None),
                'expiry_date':str(batch.expiry_date) if batch and batch.expiry_date else str(issue.expiry_date) if kind=='pharmacy' and issue.expiry_date else None,
                'store':issue.store.name if kind=='inventory' and issue.store else None,
                'returnable':str(max(Decimal(0),-issue.quantity_change-used.get(str(issue.id),Decimal(0))))})
    return records


def receive(service, dispense, payload, actor, context):
    db=service.db
    if payload.request_id:
        existing=next((e for e in dispense.return_history or [] if e.get('request_id')==payload.request_id),None)
        if existing:
            if Decimal(existing['quantity'])!=payload.quantity or existing['restocked']!=payload.restock or (payload.source_issue_id and existing['source_issue_id']!=str(payload.source_issue_id)):
                raise AppException(409,'return_request_conflict','This request identifier was already used for a different return')
            return dispense
    if not payload.inspected or not (payload.note or '').strip():
        raise AppException(422,'return_inspection_required','Confirm physical receipt/inspection and record a reason before returning medicine')
    if dispense.status in {'pending','cancelled'} or not dispense.is_active:
        raise AppException(409,'return_not_issued','Only issued medicine can be physically returned')
    if payload.quantity>dispense.quantity-dispense.returned_quantity:
        raise AppException(409,'pharmacy_return_exceeds_dispense','Return quantity exceeds remaining dispensed quantity')
    # Legacy aggregated returns cannot identify which original batch they consumed.
    recorded=sum((Decimal(e['quantity']) for e in dispense.return_history or []),Decimal(0))
    if recorded != dispense.returned_quantity:
        raise AppException(409,'return_legacy_reconciliation','Earlier returns need batch reconciliation by a supervisor before another return')
    options=[s for s in sources(db,dispense) if Decimal(s['returnable'])>0]
    selected=next((s for s in options if s['id']==str(payload.source_issue_id)),None) if payload.source_issue_id else options[0] if len(options)==1 else None
    if not selected:
        raise AppException(422,'return_issue_required','Select the original batch/store issue shown on the issued medicine')
    if payload.quantity>Decimal(selected['returnable']):
        raise AppException(409,'return_exceeds_issue','Return no more than the remaining quantity from the selected original issue')
    if payload.restock and selected['expiry_date'] and date.fromisoformat(selected['expiry_date'])<date.today():
        raise AppException(409,'return_expired','Expired medicine may be received for disposal but cannot be returned to saleable stock')
    movement_id=None
    if payload.restock:
        if selected['kind']=='inventory':
            issue=db.get(InventoryStockTransaction,UUID(selected['id']))
            item=db.scalar(select(InventoryItem).where(InventoryItem.id==issue.item_id).with_for_update())
            balance=db.scalar(select(InventoryStoreItem).where(InventoryStoreItem.item_id==issue.item_id,InventoryStoreItem.store_id==issue.store_id).with_for_update())
            batch=db.scalar(select(StockBatch).where(StockBatch.id==issue.batch_id).with_for_update()) if issue.batch_id else None
            if not item or not item.is_active or not balance or not balance.is_active or (issue.batch_id and (not batch or not batch.is_active)) or (issue.store and (not issue.store.is_active or (actor.branch_id and issue.store.branch_id and actor.branch_id!=issue.store.branch_id))):
                raise AppException(409,'return_stock_unavailable','Original stock location is unavailable; a supervisor must reconcile it')
            if actor.branch_id and item.branch_id and actor.branch_id!=item.branch_id:
                raise AppException(403,'forbidden','Original stock belongs to another branch')
            if batch and batch.expiry_date and batch.expiry_date < date.today():
                raise AppException(409,"return_expired","Expired medicine cannot enter saleable stock")
            before=Decimal(balance.quantity_on_hand);balance.quantity_on_hand=before+payload.quantity;balance.updated_by=actor.id
            item.stock_quantity=Decimal(item.stock_quantity)+payload.quantity;item.updated_by=actor.id
            if batch:
                batch.quantity=Decimal(batch.quantity)+payload.quantity;batch.total_cost=batch.quantity*batch.unit_cost;batch.updated_by=actor.id
                item.stock_value=Decimal(item.stock_value or 0)+payload.quantity*batch.unit_cost
            movement=InventoryStockTransaction(id=uuid4(),item_id=item.id,batch_id=issue.batch_id,store_id=issue.store_id,transaction_type='dispense_return_in',reference_type='pharmacy_dispense_return',reference_id=dispense.id,quantity_change=payload.quantity,stock_before=before,stock_after=balance.quantity_on_hand,note=payload.note,created_by=actor.id,updated_by=actor.id)
            db.add(movement);movement_id=str(movement.id)
        else:
            issue=db.get(PharmacyStockMovement,UUID(selected['id']))
            medicine=db.scalar(select(PharmacyMedicine).where(PharmacyMedicine.id==issue.medicine_id).with_for_update())
            if not medicine or not medicine.is_active or (actor.branch_id and medicine.branch_id and actor.branch_id!=medicine.branch_id):
                raise AppException(409,'return_stock_unavailable','Original medicine stock is unavailable')
            movement=service._change_stock(medicine=medicine,delta=payload.quantity,actor=actor,movement_type='dispense_return_in',reference_type='dispense_return',reference_id=dispense.id,batch_no=issue.batch_no,expiry_date=issue.expiry_date,note=payload.note)
            movement_id=str(movement.id)
    entry={'id':str(uuid4()),'request_id':payload.request_id,'source_issue_id':selected['id'],'quantity':str(payload.quantity),'restocked':payload.restock,'inspected_by':str(actor.id),'received_at':datetime.now(UTC).isoformat(),'reason':payload.note,'stock_movement_id':movement_id,**{k:selected[k] for k in ['kind','batch_no','expiry_date','store']}}
    dispense.return_history=[*(dispense.return_history or []),entry]
    dispense.returned_quantity+=payload.quantity;dispense.return_note=payload.note;dispense.updated_by=actor.id
    dispense.status='returned' if dispense.returned_quantity==dispense.quantity else 'partially_returned'
    # A physical return does not authorize another issue against the same prescription.
    service._commit_and_log(actor=actor,action='pharmacy.dispense.return',entity_type='pharmacy_dispense',entity_id=str(dispense.id),detail=entry,context=context)
    db.refresh(dispense)
    return dispense
