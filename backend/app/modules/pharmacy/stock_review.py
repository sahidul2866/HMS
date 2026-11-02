"""Evidence-backed stock corrections and independently reviewed disposal records."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from app.core.exceptions import AppException
from app.models.inventory import InventoryItem, InventoryStoreItem, StockBatch
from app.models.pharmacy import PharmacyDispense, PharmacyStockReview, PharmacyMedicine
from app.modules.pharmacy.physical_returns import sources
from app.modules.pharmacy.service import PharmacyService


def fail(code, message, status=409):
    raise AppException(status, code, message)


def branch(actor, entity):
    if actor.branch_id and entity.branch_id and actor.branch_id != entity.branch_id:
        fail('forbidden', 'Record belongs to another branch', 403)


def dispense(db, identifier, actor):
    row = db.scalar(select(PharmacyDispense).where(PharmacyDispense.id == identifier).with_for_update().execution_options(populate_existing=True))
    if not row or not row.is_active:
        fail('dispense_not_found', 'Dispense record not found', 404)
    branch(actor, row)
    return row


def receipt(row, identifier):
    entry = next((e for e in row.return_history or [] if e['id'] == str(identifier)), None)
    if not entry or entry.get('restocked') or entry.get('disposal_status') == 'historically_disposed':
        fail('disposal_not_pending', 'Select a physical receipt held for disposal')
    return entry


def count_target(db, details, actor):
    batch = db.get(StockBatch, UUID(details['batch_id']))
    if not batch or not batch.is_active:
        fail('batch_unavailable', 'Select an active inventory batch', 404)
    # Same item/store/batch lock order as physical returns. Refresh locked snapshots.
    item = db.scalar(select(InventoryItem).where(InventoryItem.id == batch.item_id).with_for_update().execution_options(populate_existing=True))
    balance = db.scalar(select(InventoryStoreItem).where(InventoryStoreItem.item_id == batch.item_id, InventoryStoreItem.store_id == batch.store_id).with_for_update().execution_options(populate_existing=True))
    batch = db.scalar(select(StockBatch).where(StockBatch.id == batch.id).with_for_update().execution_options(populate_existing=True))
    branch(actor, item)
    if not item.is_active or not balance or not balance.is_active or not batch.store or not batch.store.is_active:
        fail('stock_unavailable', 'Original stock location is inactive or missing')
    branch(actor, batch.store)
    snapshot = {'batch':str(batch.quantity), 'store':str(balance.quantity_on_hand), 'item':str(item.stock_quantity), 'reserved':str(balance.reserved_quantity), 'unit_cost':str(batch.unit_cost)}
    return item, balance, batch, snapshot


def validate_allocation(db, data, actor):
    row = dispense(db, UUID(data['dispense_id']), actor)
    recorded = sum((Decimal(e['quantity']) for e in row.return_history or []), Decimal(0))
    quantity = Decimal(data['quantity'])
    if quantity > Decimal(row.returned_quantity) - recorded:
        fail('reconciliation_exceeds_unallocated', 'Allocate no more than the historical returned quantity without source evidence')
    source = next((s for s in sources(db, row) if s['id'] == data['source_issue_id']), None)
    if not source or quantity > Decimal(source['returnable']):
        fail('reconciliation_source_invalid', 'Quantity exceeds the remaining original issue allocation')
    return row, source


def submit(db, kind, payload, actor, context):
    data = payload.model_dump(mode='json')
    record_branch = actor.branch_id
    if kind == 'count':
        item, balance, batch, snapshot = count_target(db, data, actor)
        record_branch = item.branch_id
        data.update(snapshot=snapshot, item_name=item.name, batch_no=batch.batch_no, store=batch.store.name)
        if Decimal(data['counted_quantity']) - batch.quantity + balance.quantity_on_hand < balance.reserved_quantity:
            fail('reserved_stock', 'Count would reduce available stock below reserved quantities; resolve reservations first')
    elif kind == 'legacy_return':
        row, source = validate_allocation(db, data, actor)
        record_branch = row.branch_id
        data.update(medicine_name=row.medicine_name, source=source)
    elif kind == 'disposal':
        row = dispense(db, payload.dispense_id, actor)
        record_branch = row.branch_id
        entry = receipt(row, payload.receipt_id)
        if entry.get('disposal_status') in {'submitted', 'approved'}:
            fail('disposal_already_recorded', 'A disposal record already exists for this receipt')
        try:
            performed = datetime.fromisoformat(data['performed_at'].replace('Z', '+00:00'))
            received = datetime.fromisoformat(entry['received_at'])
            if not performed.tzinfo or performed > datetime.now(UTC) or performed < received:
                raise ValueError()
        except ValueError:
            fail('disposal_time_invalid', 'Record the actual disposal time, including timezone, after receipt and no later than now', 422)
        if not data['method'].strip() or not data['witness'].strip():
            fail('disposal_evidence_required', 'Record the method and witness', 422)
        data.update(quantity=entry['quantity'], medicine_name=row.medicine_name, batch_no=entry.get('batch_no'))
    review = PharmacyStockReview(kind=kind, branch_id=record_branch, details=data, status='submitted', submitted_by_id=actor.id, created_by=actor.id, updated_by=actor.id)
    db.add(review); db.flush()
    if kind == 'disposal':
        row.return_history = [{**e, 'disposal_status':'submitted', 'disposal_review_id':str(review.id)} if e['id'] == data['receipt_id'] else e for e in row.return_history]
        row.updated_by = actor.id
    PharmacyService(db)._commit_and_log(actor=actor, action='pharmacy.stock_review.submit', entity_type='pharmacy_stock_review', entity_id=str(review.id), detail={'kind':kind, **data}, context=context)
    return serialize(review)


def decide(db, identifier, payload, actor, context):
    review = db.scalar(select(PharmacyStockReview).where(PharmacyStockReview.id == identifier).with_for_update().execution_options(populate_existing=True))
    if not review or not review.is_active:
        fail('review_not_found', 'Stock review not found', 404)
    branch(actor, review)
    if review.submitted_by_id == actor.id:
        fail('reviewer_separation', 'A different supervisor must review this submission', 403)
    target_status = 'approved' if payload.decision == 'approve' else 'rejected'
    if review.status != 'submitted':
        if review.status == target_status:
            return serialize(review)
        fail('review_already_decided', 'This review already has a final decision')
    data = review.details
    if review.kind == 'count' and payload.decision == 'approve':
        item, balance, batch, current = count_target(db, data, actor)
        if current != data['snapshot']:
            fail('stock_count_stale', 'Stock changed after counting. Reject this submission and perform a fresh count')
        delta = Decimal(data['counted_quantity']) - batch.quantity
        if balance.quantity_on_hand + delta < balance.reserved_quantity or item.stock_quantity + delta < 0:
            fail('reserved_stock', 'Correction would violate available or reserved stock')
        from app.modules.inventory.service import InventoryService
        InventoryService(db)._change_store_stock(store=batch.store, item=item, delta=delta, actor=actor, movement_type='count_reconciliation', reference_type='pharmacy_stock_review', reference_id=str(review.id), batch=batch, note=data['reason'], unit_cost=batch.unit_cost)
        batch.quantity = Decimal(data['counted_quantity'])
        batch.total_cost = batch.quantity * batch.unit_cost
        batch.updated_by = actor.id
    elif review.kind == 'legacy_return' and payload.decision == 'approve':
        row, source = validate_allocation(db, data, actor)
        disposition = data['disposition']
        entry = {'id':str(uuid4()), 'source_issue_id':data['source_issue_id'], 'quantity':data['quantity'], 'restocked':disposition=='historically_restocked', 'inspected_by':str(review.submitted_by_id), 'received_at':datetime.now(UTC).isoformat(), 'reason':data['reason'], 'stock_movement_id':None, 'historical_reconciliation':True, 'evidence_reference':data['evidence_reference'], 'review_id':str(review.id), 'reviewed_by':str(actor.id), 'disposal_status':'historically_disposed' if disposition=='historically_disposed' else 'pending' if disposition=='held_for_disposal' else None, **{k:source[k] for k in ['kind','batch_no','expiry_date','store']}}
        row.return_history = [*(row.return_history or []), entry]
        row.updated_by = actor.id
        # Provenance only: historical stock restoration is never repeated here.
    elif review.kind == 'disposal':
        row = dispense(db, UUID(data['dispense_id']), actor)
        entry = receipt(row, data['receipt_id'])
        if entry.get('disposal_review_id') != str(review.id):
            fail('disposal_review_mismatch', 'Receipt no longer matches this disposal submission')
        row.return_history = [{**e, 'disposal_status':target_status, 'disposal_reviewed_by':str(actor.id)} if e['id'] == data['receipt_id'] else e for e in row.return_history]
        row.updated_by = actor.id
    review.status = target_status; review.reviewed_by_id = actor.id
    review.review_note = payload.note; review.reviewed_at = datetime.now(UTC).isoformat(); review.updated_by = actor.id
    PharmacyService(db)._commit_and_log(actor=actor, action='pharmacy.stock_review.'+target_status, entity_type='pharmacy_stock_review', entity_id=str(review.id), detail={'kind':review.kind, 'note':payload.note}, context=context)
    return serialize(review)


def serialize(row):
    return {'id':str(row.id), 'kind':row.kind, 'status':row.status, 'details':row.details, 'submitted_by_id':str(row.submitted_by_id), 'submitted_by':row.submitted_by.full_name, 'reviewed_by':row.reviewed_by.full_name if row.reviewed_by else None, 'review_note':row.review_note, 'reviewed_at':row.reviewed_at, 'created_at':row.created_at.isoformat()}


def workspace(db, actor):
    query = select(PharmacyDispense).where(PharmacyDispense.is_active.is_(True), PharmacyDispense.returned_quantity > 0)
    reviews = select(PharmacyStockReview).where(PharmacyStockReview.is_active.is_(True))
    batches = select(StockBatch).join(InventoryItem).where(StockBatch.is_active.is_(True), InventoryItem.is_active.is_(True))
    if actor.branch_id:
        query = query.where(PharmacyDispense.branch_id == actor.branch_id)
        reviews = reviews.where(PharmacyStockReview.branch_id == actor.branch_id)
        batches = batches.where(InventoryItem.branch_id == actor.branch_id)
    pending = []; legacy = []
    for row in db.scalars(query):
        recorded = sum((Decimal(e['quantity']) for e in row.return_history or []), Decimal(0))
        if row.returned_quantity > recorded:
            legacy.append({'dispense_id':str(row.id), 'medicine_name':row.medicine_name, 'unallocated_quantity':str(row.returned_quantity-recorded), 'sources':sources(db,row)})
        for e in row.return_history or []:
            if not e.get('restocked') and e.get('disposal_status') not in {'submitted','approved','historically_disposed'}:
                pending.append({'dispense_id':str(row.id), 'medicine_name':row.medicine_name, **e})
    return {'reviews':[serialize(r) for r in db.scalars(reviews.order_by(PharmacyStockReview.created_at.desc()))], 'pending_disposals':pending, 'legacy_returns':legacy, 'batches':[{'id':str(b.id), 'item_name':b.item.name, 'batch_no':b.batch_no, 'quantity':str(b.quantity), 'store':b.store.name if b.store else 'Unavailable'} for b in db.scalars(batches.order_by(StockBatch.created_at.desc()))]}
