"""Book verified cost of physical issues; specialized receipt/meal flows retain their postings."""
from decimal import Decimal
from app.modules.accounting.pharmacy_posting import enabled
from app.modules.accounting.service import AccountingService
from app.utils.accounting_time import today_local


def post_stock_movement(db,actor,transaction):
    from app.modules.accounting.controls import policy_for
    if not policy_for(db,actor.branch_id,today_local()):return
    if transaction.reference_type in {'catering_meal','stock_receiving','receiving','inventory_receiving'}:return
    if transaction.transaction_type in {'transfer_in','transfer_out','purchase_in','receive','receiving'}:return
    from app.core.exceptions import AppException
    if transaction.cost_amount is None:raise AppException(422,'inventory_cost_required','Record verified stock cost or a reconciled opening valuation before posting this movement')
    amount=abs(transaction.cost_amount)
    if transaction.quantity_change<0:
        account=AccountingService(db)._find_account(actor.branch_id,None,'1300')
        if not account or amount>account.current_balance:raise AppException(409,'inventory_control_opening','Reconcile inventory control opening balances before issuing or writing off stock')
    if not amount:return
    offset='5030' if transaction.reference_type=='pharmacy_dispense' else '5040' if transaction.transaction_type in {'issue','issue_out'} else '5190'
    lines=[(offset,'Verified stock issue / adjustment',amount,0),('1300','Inventory / Supplies',0,amount)] if transaction.quantity_change<0 else [('1300','Inventory / Supplies',amount,0),(offset,'Stock return / adjustment',0,amount)]
    AccountingService(db)._create_auto_entry(actor,'inventory_cost',str(transaction.id),today_local(),'Verified inventory movement '+transaction.transaction_type,lines)


def approve_adjustment(db,identity,actor,reason):
    from sqlalchemy import select
    from app.models.inventory import StockAdjustment,InventoryItem
    from app.modules.inventory.service import InventoryService
    from app.modules.support_posting.service import lock_branch
    from app.modules.accounting.management import AccountingManagement
    from app.core.exceptions import AppException
    lock_branch(db,actor)
    adjustment=db.scalar(select(StockAdjustment).where(StockAdjustment.id==identity).with_for_update())
    item=db.get(InventoryItem,adjustment.item_id) if adjustment else None
    if not adjustment or not item or item.branch_id!=actor.branch_id:raise AppException(404,'stock_adjustment_not_found','Branch adjustment request not found')
    if adjustment.status in {'posted','approved'}:return adjustment
    if adjustment.status not in {'draft','pending'}:raise AppException(409,'stock_adjustment_state','Only a pending adjustment can be approved')
    if adjustment.created_by==actor.id:raise AppException(403,'stock_adjustment_self_approval','Another authorized reviewer must approve the stock adjustment')
    service=InventoryService(db);item=service._get_item_for_update(str(item.id));store=service._get_store_for_update(str(adjustment.store_id),actor)
    batch=service._get_batch_for_update(str(adjustment.batch_id)) if adjustment.batch_id else None
    delta=adjustment.quantity_change if adjustment.adjustment_type.lower() in {'addition','restock'} else -adjustment.quantity_change
    if batch and batch.quantity+delta<0:raise AppException(409,'stock_adjustment_shortage','Physical batch quantity is insufficient')
    if batch:batch.quantity+=delta
    service._change_store_stock(store=store,item=item,delta=delta,actor=actor,movement_type='adjustment',reference_type='adjustment',reference_id=str(adjustment.id),batch=batch,note=adjustment.reason)
    adjustment.status='approved';adjustment.approved_by=actor.id;adjustment.updated_by=actor.id
    AccountingManagement(db).audit(actor,'inventory.adjustment.approve',adjustment.id,{'reason':reason,'quantity_delta':str(delta)});db.commit();return adjustment
