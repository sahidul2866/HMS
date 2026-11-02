from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from test_opd_workflow_integration import database, db, seed
from app.models.inventory import InventoryItem,InventoryStore,InventoryStoreItem,StockBatch,InventoryStockTransaction
from app.models.pharmacy import PharmacyDispense
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import PharmacyDispenseReturnCreate
from app.core.exceptions import AppException


def setup_issue(db):
    actor,_,patient,_=seed(db)
    item=InventoryItem(branch_id=actor.branch_id,name='Physical return medicine',stock_quantity=3)
    store=InventoryStore(branch_id=actor.branch_id,code='RET-'+uuid4().hex[:8],name='Original store',store_type='pharmacy')
    db.add_all([item,store]);db.flush()
    balance=InventoryStoreItem(item_id=item.id,store_id=store.id,quantity_on_hand=3,reserved_quantity=0)
    batch=StockBatch(item_id=item.id,store_id=store.id,batch_no='ORIGINAL',quantity=3,unit_cost=2,total_cost=6,expiry_date=date.today()+timedelta(days=30))
    dispense=PharmacyDispense(branch_id=actor.branch_id,patient_id=patient.id,medicine_name=item.name,quantity=7,returned_quantity=0,unit_price=5,total_price=35,status='dispensed',dispensed_by_user_id=actor.id)
    db.add_all([balance,batch,dispense]);db.flush()
    issue=InventoryStockTransaction(item_id=item.id,store_id=store.id,batch_id=batch.id,transaction_type='dispense_out',reference_type='pharmacy_dispense',reference_id=dispense.id,quantity_change=-7,stock_before=10,stock_after=3,created_by=actor.id)
    db.add(issue);db.commit()
    return actor,item,balance,batch,dispense,issue


def test_partial_restock_and_disposal_reconcile_only_original_issue(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db)
    service=PharmacyService(db)
    def receive(qty,restock):return service.return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=qty,source_issue_id=issue.id,restock=restock,inspected=True,note='Sealed inspected return' if restock else 'Damaged received for disposal'),actor,{})
    receive(4,True)
    assert item.stock_quantity==7 and balance.quantity_on_hand==7 and batch.quantity==7 and batch.total_cost==14
    receive(2,False)
    assert item.stock_quantity==7 and balance.quantity_on_hand==7 and batch.quantity==7
    assert dispense.returned_quantity==6 and len(dispense.return_history)==2
    receive(1,True)
    assert item.stock_quantity==8 and balance.quantity_on_hand==8 and batch.quantity==8
    assert dispense.status=='returned'
    with pytest.raises(AppException):receive(1,True)
    assert batch.quantity==8


def test_expired_and_uninspected_goods_cannot_increase_stock(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db)
    service=PharmacyService(db)
    with pytest.raises(AppException):service.return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=1,note='Not inspected'),actor,{})
    batch.expiry_date=date.today()-timedelta(days=1);db.commit()
    with pytest.raises(AppException):service.return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=1,inspected=True,restock=True,note='Expired'),actor,{})
    assert batch.quantity==3 and dispense.returned_quantity==0


def test_retry_is_idempotent_and_wrong_source_is_rejected(db):
    actor,item,balance,batch,dispense,issue=setup_issue(db)
    service=PharmacyService(db)
    payload=PharmacyDispenseReturnCreate(quantity=2,source_issue_id=issue.id,restock=True,inspected=True,note='Inspected sealed',request_id='return-request-001')
    service.return_dispense(dispense.id,payload,actor,{})
    service.return_dispense(dispense.id,payload,actor,{})
    assert batch.quantity==5 and dispense.returned_quantity==2 and len(dispense.return_history)==1
    with pytest.raises(AppException):service.return_dispense(dispense.id,PharmacyDispenseReturnCreate(quantity=1,source_issue_id=uuid4(),restock=True,inspected=True,note='Unknown batch'),actor,{})
    assert batch.quantity==5


def test_issue_permission_does_not_grant_physical_return_permission(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies.auth import get_current_user
    from app.core.database import get_db
    actor,_,_,_=seed(db)
    actor.direct_permissions=[p for p in actor.direct_permissions if p.code=='pharmacy.dispense']
    db.flush()
    original=app.dependency_overrides.copy()
    app.dependency_overrides[get_db]=lambda:db
    app.dependency_overrides[get_current_user]=lambda:actor
    try:
        response=TestClient(app).post('/api/v1/pharmacy/dispenses/'+str(uuid4())+'/return',json={'quantity':1,'inspected':True,'restock':True,'note':'Receipt needs separate permission'})
        assert response.status_code==403
    finally:
        app.dependency_overrides=original


def test_returns_do_not_increase_the_remaining_prescription_issue(db):
    from app.models.encounter import OPDVisit,OPDVisitOrder
    actor,item,_,_,dispense,_=setup_issue(db)
    visit=OPDVisit(branch_id=actor.branch_id,patient_id=dispense.patient_id,visit_number='RETURN-RX-'+uuid4().hex[:8],visit_date=date.today(),department_name='Review',consulting_doctor_name='Review doctor',registered_by_user_id=actor.id)
    db.add(visit);db.flush()
    order=OPDVisitOrder(visit_id=visit.id,order_type='prescription',item_name=item.name,quantity=5,status='in_progress')
    db.add(order);db.flush()
    dispense.source_visit_order_id=order.id;dispense.source_visit_id=visit.id;dispense.quantity=3;dispense.returned_quantity=2;dispense.status='partially_returned';db.commit()
    pending=PharmacyService(db).list_pending_prescriptions(actor)
    row=next(row for row in pending if row.order_id==order.id)
    assert row.remaining_quantity==2 and row.dispensed_quantity==3


def test_physical_return_quantity_matches_persisted_stock_precision():
    with pytest.raises(ValueError):
        PharmacyDispenseReturnCreate(quantity='0.001',inspected=True,note='Too precise for stock ledger')
    with pytest.raises(ValueError):
        PharmacyDispenseReturnCreate(quantity='100000000000',inspected=True,note='Too large for stock ledger')
