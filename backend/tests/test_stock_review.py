from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4
import pytest
from test_physical_returns import setup_issue
from test_opd_workflow_integration import database, db
from app.models.user import User
from app.models.branch import Branch
from app.models.inventory import InventoryStockTransaction
from app.modules.pharmacy import stock_review
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import PharmacyDispenseReturnCreate
from app.schemas.pharmacy_review import StockCountCreate, LegacyReturnAllocation, DisposalCreate, ReviewDecision
from app.core.exceptions import AppException
from sqlalchemy import select


def supervisor(db, actor):
    suffix=uuid4().hex
    user=User(branch_id=actor.branch_id,username='reviewer'+suffix,email=suffix+'@test.example',full_name='Independent Reviewer',hashed_password='unused',direct_permissions=actor.direct_permissions)
    db.add(user);db.flush();return user


def decision(note='Evidence and physical count checked', value='approve'):
    return ReviewDecision(decision=value,note=note)


def test_count_posts_once_and_separates_submitter_from_reviewer(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db);reviewer=supervisor(db,actor)
    record=stock_review.submit(db,'count',StockCountCreate(batch_id=batch.id,counted_quantity=2,reason='One unit damaged during storage',evidence_reference='COUNT-001'),actor,{})
    assert batch.quantity==3 and balance.quantity_on_hand==3
    with pytest.raises(AppException):stock_review.decide(db,record['id'],decision(),actor,{})
    stock_review.decide(db,record['id'],decision(),reviewer,{})
    stock_review.decide(db,record['id'],decision(),reviewer,{})
    assert batch.quantity==2 and batch.total_cost==4 and balance.quantity_on_hand==2 and item.stock_quantity==2
    movements=list(db.scalars(select(InventoryStockTransaction).where(InventoryStockTransaction.reference_type=='pharmacy_stock_review')))
    assert len(movements)==1 and movements[0].quantity_change==-1
    with pytest.raises(AppException):stock_review.decide(db,record['id'],decision(value='reject'),reviewer,{})


def test_count_changed_after_submission_requires_fresh_count(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db);reviewer=supervisor(db,actor)
    record=stock_review.submit(db,'count',StockCountCreate(batch_id=batch.id,counted_quantity=2,reason='Counting discrepancy found',evidence_reference='COUNT-002'),actor,{})
    batch.quantity=4;db.commit()
    with pytest.raises(AppException) as error:stock_review.decide(db,record['id'],decision(),reviewer,{})
    assert error.value.code=='stock_count_stale'
    stock_review.decide(db,record['id'],decision(value='reject'),reviewer,{})
    assert batch.quantity==4 and balance.quantity_on_hand==3


def test_disposal_requires_physical_receipt_and_independent_signoff_without_stock(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db);reviewer=supervisor(db,actor)
    PharmacyService(db).return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=2,source_issue_id=issue.id,inspected=True,note='Damaged packaging received'),actor,{})
    entry=dispense.return_history[0]
    payload=DisposalCreate(dispense_id=dispense.id,receipt_id=entry['id'],method='Approved waste contractor',witness='Witness staff 100',performed_at=datetime.now(UTC).isoformat(),reason='Damaged stock, cannot be sold',evidence_reference='MANIFEST-001')
    record=stock_review.submit(db,'disposal',payload,actor,{})
    with pytest.raises(AppException):stock_review.submit(db,'disposal',payload,actor,{})
    with pytest.raises(AppException):stock_review.decide(db,record['id'],decision(),actor,{})
    stock_review.decide(db,record['id'],decision(value='reject'),reviewer,{})
    record=stock_review.submit(db,'disposal',payload,actor,{})
    stock_review.decide(db,record['id'],decision(),reviewer,{})
    assert dispense.return_history[0]['disposal_status']=='approved'
    assert stock_review.workspace(db,actor)['pending_disposals']==[]
    assert batch.quantity==3 and balance.quantity_on_hand==3 and item.stock_quantity==3


def test_legacy_allocation_requires_evidence_and_does_not_restore_stock_twice(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db);reviewer=supervisor(db,actor)
    dispense.returned_quantity=2;dispense.status='partially_returned';db.commit()
    payload=LegacyReturnAllocation(dispense_id=dispense.id,source_issue_id=issue.id,quantity=2,disposition='historically_restocked',reason='Original issue verified from historic count sheets',evidence_reference='HISTORY-001')
    record=stock_review.submit(db,'legacy_return',payload,actor,{})
    stock_review.decide(db,record['id'],decision(),reviewer,{})
    assert dispense.returned_quantity==2 and len(dispense.return_history)==1
    assert stock_review.workspace(db,actor)['legacy_returns']==[]
    assert batch.quantity==3 and item.stock_quantity==3
    with pytest.raises(AppException):stock_review.submit(db,'legacy_return',payload,actor,{})
    PharmacyService(db).return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=1,source_issue_id=issue.id,inspected=True,restock=True,note='New physical receipt after historical reconciliation'),actor,{})
    assert batch.quantity==4 and dispense.returned_quantity==3


def test_other_branch_cannot_review_or_read_batch(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db);reviewer=supervisor(db,actor)
    record=stock_review.submit(db,'count',StockCountCreate(batch_id=batch.id,counted_quantity=2,reason='Difference checked in count',evidence_reference='COUNT-003'),actor,{})
    other=Branch(code='OTHER'+uuid4().hex[:8],name='Other Branch');db.add(other);db.flush();reviewer.branch_id=other.id;db.commit()
    assert stock_review.workspace(db,reviewer)['reviews']==[]
    with pytest.raises(AppException):stock_review.decide(db,record['id'],decision(),reviewer,{})


def test_reception_branch_queue_access_does_not_grant_prescribing(db):
    from app.utils.seed_data import ROLE_CATALOG
    from app.models.role import Role
    from app.modules.opd.service import OPDService
    from test_opd_workflow_integration import seed, visit
    actor,doctors,patient,slot=seed(db)
    current=visit(db,actor,doctors[0],patient,slot)
    codes=set(ROLE_CATALOG['RECEPTIONIST'])
    role=Role(code='REC-'+uuid4().hex,name='Test Reception',permissions=[p for p in actor.direct_permissions if p.code in codes])
    actor.direct_permissions=[];actor.roles=[role];db.flush()
    assert any(v.id==current.id for v in OPDService(db).list_visits(actor))
    assert 'opd.prescribe' not in codes and 'pharmacy.stock.approve' not in codes


def test_expired_batches_cannot_be_reissued_as_unbatched_stock(db):
    from datetime import date, timedelta
    actor,item,balance,batch,dispense,issue=setup_issue(db)
    batch.expiry_date=date.today()-timedelta(days=1);db.commit()
    service=PharmacyService(db)
    assert service._available_inventory_quantity(item)==0
    assert service._deduct_inventory_for_dispense(item=item,quantity=1,actor=actor,reference_id=dispense.id,note='Must not issue expired stock')==0
    assert batch.quantity==3 and balance.quantity_on_hand==3


def test_restock_reconciles_batch_cost_and_inventory_value(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db)
    item.stock_value=6;db.commit()
    PharmacyService(db).return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=2,source_issue_id=issue.id,inspected=True,restock=True,note='Inspected sealed return with cost restoration'),actor,{})
    assert batch.total_cost==10 and item.stock_value==10


def test_pharmacy_submit_permission_does_not_grant_approval(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    actor,item,balance,batch,dispense,issue=setup_issue(db)
    actor.direct_permissions=[p for p in actor.direct_permissions if p.code in {'pharmacy.stock.adjust','pharmacy.return'}];db.flush()
    original=app.dependency_overrides.copy()
    app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:actor
    try:
        response=TestClient(app).post('/api/v1/pharmacy/stock-reviews/'+str(uuid4())+'/decision',json={'decision':'approve','note':'Pharmacy cannot approve its own review'})
        assert response.status_code==403
    finally:app.dependency_overrides=original
