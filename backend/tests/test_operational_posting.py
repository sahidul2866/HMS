"""Connected, transactional posting/correction/coordination acceptance on PostgreSQL."""
from datetime import UTC,date,datetime,timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from test_opd_workflow_integration import database,db,seed
from app.core.exceptions import AppException
from app.models.user import User
from app.models.catering import CateringMealPlan,CateringMealTask,CateringStaffMealOrder
from app.models.inventory import InventoryItem,InventoryStore,InventoryStoreItem,InventoryStockTransaction,StockBatch
from app.models.operational_posting import OperationalPosting,HRPayrollAdjustment
from app.models.accounting import Account,JournalEntry
from app.modules.catering.service import CateringService
from app.modules.hr.service import HRService
from app.modules.billing.service import BillingServiceManager
from app.schemas.catering import CateringDietOrderCreate,CateringDietOrderUpdate,CateringMealGenerateRequest,CateringMealStatusUpdate,CateringStaffMealCreate
from app.schemas.hr import HREmployeeCreate,HRSalaryStructureCreate,HRPayrollRunCreate,HRPayrollAdjustmentCreate
from app.schemas.billing import BillingPaymentCreate,BillingReturnCreate,BillingReturnItemCreate


def kitchen(db,quantity=10,batch=False):
    actor,_,patient,_=seed(db);svc=CateringService(db);regular=next(x for x in svc.list_diet_types(actor) if x.code=='REGULAR')
    item=InventoryItem(branch_id=actor.branch_id,name='Synthetic ingredient',is_batch_tracked=batch,stock_quantity=quantity,stock_value=quantity*10)
    store=InventoryStore(branch_id=actor.branch_id,code='KITCHEN',name='Kitchen');db.add_all([item,store]);db.flush()
    db.add(InventoryStoreItem(store_id=store.id,item_id=item.id,quantity_on_hand=quantity))
    plan=CateringMealPlan(branch_id=actor.branch_id,diet_type_id=regular.id,name='Lunch',meal_type='lunch',billable_amount=150,inventory_item_id=item.id,inventory_store_id=store.id,inventory_quantity=2);db.add(plan);db.flush()
    order=svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=regular.id,meal_plan_id=plan.id,start_at=datetime.now(UTC)-timedelta(days=2)),actor,{})
    task=svc.generate_meals(CateringMealGenerateRequest(meal_date=date.today()),actor,{})[0]
    return actor,patient,svc,item,store,plan,order,task


def deliver(svc,task,actor):
    for status in ['preparing','ready']:svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status=status),actor,{})
    for status in ['out_for_delivery','delivered']:svc.update_meal_status(task.id,CateringMealStatusUpdate(delivery_status=status),actor,{})


def balance(db,actor,code):
    return db.scalar(select(Account.current_balance).where(Account.branch_id==actor.branch_id,Account.account_code==code)) or Decimal(0)


def test_meal_consumes_stock_invoices_collects_and_returns_without_restock(db):
    actor,patient,svc,item,store,plan,order,task=kitchen(db);deliver(svc,task,actor)
    assert item.stock_quantity==8 and task.inventory_status=='consumed' and task.billing_invoice_id
    billing=BillingServiceManager(db);invoice=billing.get_invoice(task.billing_invoice_id,actor)
    assert invoice.total_amount==150 and balance(db,actor,'1100')==150 and balance(db,actor,'5200')==20
    invoice=billing.create_payment(invoice.id,BillingPaymentCreate(amount=150,payment_method='cash'),actor,{})
    invoice=billing.create_return(invoice.id,BillingReturnCreate(reason='Synthetic service credit',items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=Decimal('.5'))]),actor,{})
    assert invoice.due_amount==0 and balance(db,actor,'1001')==75 and balance(db,actor,'1100')==0
    assert item.stock_quantity==8
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(delivery_status='delivered'),actor,{})
    assert db.scalar(select(func.count()).select_from(OperationalPosting).where(OperationalPosting.source_id==task.id,OperationalPosting.event=='invoice'))==1
    for entry in db.scalars(select(JournalEntry)):assert entry.total_debit==entry.total_credit


def test_shortage_rolls_back_preparation_and_all_posting(db):
    actor,_,svc,item,_,_,_,task=kitchen(db,quantity=1)
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),actor,{})
    db.rollback();db.refresh(task);db.refresh(item)
    assert task.preparation_status=='scheduled' and item.stock_quantity==1
    assert db.scalar(select(func.count()).select_from(InventoryStockTransaction))==0


def test_fefo_split_batches_and_frozen_usage_quantity(db):
    actor,_,svc,item,store,plan,_,task=kitchen(db,quantity=3,batch=True)
    batches=[StockBatch(item_id=item.id,store_id=store.id,batch_no='B'+str(i),quantity=q,unit_cost=10,total_cost=q*10,expiry_date=date.today()+timedelta(days=i+1)) for i,q in enumerate([1,2])];db.add_all(batches)
    plan.inventory_quantity=3;db.commit()  # Existing ticket retains the two-unit recipe snapshot.
    svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),actor,{})
    assert [b.quantity for b in batches]==[0,1] and item.stock_quantity==1
    assert db.scalar(select(func.count()).select_from(InventoryStockTransaction))==2


def payroll_setup(db):
    actor,_,_,_=seed(db);svc=HRService(db)
    employee=svc.create_employee(HREmployeeCreate(full_name='Posting staff',joining_date=date(2026,1,1)),actor)
    svc.upsert_salary(HRSalaryStructureCreate(employee_id=employee.id,effective_from=date(2026,1,1),basic_salary=26000),actor)
    reviewer=User(branch_id=actor.branch_id,username='reviewer',email='reviewer@example.test',full_name='Reviewer',hashed_password='unused',direct_permissions=actor.direct_permissions);db.add(reviewer);db.commit()
    return actor,reviewer,svc,employee


def test_staff_meal_and_reviewed_adjustment_are_deducted_once(db):
    actor,reviewer,svc,employee=payroll_setup(db);catering=CateringService(db)
    meal=catering.create_staff_meal(CateringStaffMealCreate(employee_id=employee.id,meal_date=date(2026,10,15),meal_type='lunch',amount=40,payroll_deductible=True,eligibility_type='paid'),actor,{})
    for status in ['issued','served']:catering.update_staff_meal_status(meal.id,status,actor,{})
    adjustment=svc.create_adjustment(HRPayrollAdjustmentCreate(employee_id=employee.id,target_month='2026-10',kind='earning',amount=100,reason='Reviewed synthetic arrears'),actor)
    with pytest.raises(AppException):svc.decide_adjustment(adjustment.id,'approved',actor)
    svc.decide_adjustment(adjustment.id,'approved',reviewer)
    run=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    assert run.total_net_salary==26060 and meal.deduction_state=='reserved'
    svc.approve_payroll(run.id,reviewer,status='approved');svc.approve_payroll(run.id,reviewer,status='paid');svc.approve_payroll(run.id,reviewer,status='paid')
    assert meal.deduction_state=='deducted' and adjustment.status=='applied' and balance(db,actor,'1150')==0
    assert balance(db,actor,'2200')==0 and balance(db,actor,'1001')==-26060
    following=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-11'),actor)
    assert following.total_net_salary==26000


def test_future_salary_revision_and_correction_preserve_paid_snapshot(db):
    actor,reviewer,svc,employee=payroll_setup(db)
    paid=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    svc.approve_payroll(paid.id,reviewer,status='approved');svc.approve_payroll(paid.id,reviewer,status='paid')
    source=paid.items[0]
    svc.upsert_salary(HRSalaryStructureCreate(employee_id=employee.id,effective_from=date(2026,11,1),basic_salary=28000),actor)
    adjustment=svc.create_adjustment(HRPayrollAdjustmentCreate(employee_id=employee.id,source_payroll_item_id=source.id,target_month='2026-11',kind='deduction',amount=500,reason='Correct earlier overpayment'),actor);svc.decide_adjustment(adjustment.id,'approved',reviewer)
    run=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-11'),actor)
    assert run.total_net_salary==27500 and source.basic_salary==26000 and paid.status=='paid'
    late=svc.create_adjustment(HRPayrollAdjustmentCreate(employee_id=employee.id,target_month='2026-11',kind='earning',amount=200,reason='Additional reviewed arrears'),actor);svc.decide_adjustment(late.id,'approved',reviewer)
    svc.recalculate_payroll(run.id,actor)
    assert run.total_net_salary==27700 and source.net_salary==26000
    svc.approve_payroll(run.id,reviewer,status='approved')
    with pytest.raises(AppException):svc.recalculate_payroll(run.id,actor)


def test_pending_npo_holds_other_diets_and_preserves_consumed_waste(db):
    actor,patient,svc,item,_,_,order,task=kitchen(db)
    svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),actor,{})
    npo=next(x for x in svc.list_diet_types(actor) if x.code=='NPO')
    hold=svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=npo.id,start_at=datetime.now(UTC)-timedelta(days=1)),actor,{})
    assert hold.status=='pending_approval' and task.delivery_status=='cancelled' and task.inventory_status=='consumed_waste' and item.stock_quantity==8
    assert svc.generate_meals(CateringMealGenerateRequest(meal_date=date.today()),actor,{})==[]
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(delivery_status='out_for_delivery'),actor,{})
    svc.update_diet_order(hold.id,CateringDietOrderUpdate(patient_id=patient.id,diet_type_id=npo.id,start_at=hold.start_at,status='stopped'),actor,{})
    assert len(svc.generate_meals(CateringMealGenerateRequest(meal_date=date.today()),actor,{}))==1


def test_legacy_staff_meal_flags_are_not_automatically_deducted(db):
    actor,_,svc,employee=payroll_setup(db)
    legacy=CateringStaffMealOrder(branch_id=actor.branch_id,employee_id=employee.id,staff_name=employee.full_name,meal_date=date(2026,10,1),meal_type='lunch',amount=50,status='served',payroll_deductible=True,deduction_state='manual_review');db.add(legacy);db.commit()
    run=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    assert run.total_net_salary==26000 and legacy.payroll_item_id is None


def test_billable_trip_posts_fare_and_receipt_once(db):
    from test_support_workflows import transport_case
    from app.schemas.transport import TransportTripStatusUpdate
    actor,svc,request,trip=transport_case(db)
    request.billing_required=True;trip.charges={'total':'250'};db.commit()
    for status in ['dispatched','arrived_at_pickup','patient_picked_up','in_transit','arrived_at_destination','completed']:
        svc.update_trip_status(trip.id,TransportTripStatusUpdate(status=status),actor,{})
    db.commit();assert trip.billing_invoice_id and trip.billing_status=='invoiced'
    svc.update_trip_status(trip.id,TransportTripStatusUpdate(status='completed'),actor,{})
    billing=BillingServiceManager(db);billing.create_payment(trip.billing_invoice_id,BillingPaymentCreate(amount=250,payment_method='cash'),actor,{})
    assert balance(db,actor,'4400')==250 and balance(db,actor,'1100')==0
    assert db.scalar(select(func.count()).select_from(OperationalPosting).where(OperationalPosting.source_id==trip.id,OperationalPosting.event=='invoice'))==1


def test_inventory_bootstrap_does_not_duplicate_allocated_stock(db):
    from app.modules.inventory.service import InventoryService
    actor,_,svc,item,_,_,_,task=kitchen(db)
    svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),actor,{})
    InventoryService(db).list_stores(user=actor)
    assert db.scalar(select(func.sum(InventoryStoreItem.quantity_on_hand)).where(InventoryStoreItem.item_id==item.id))==item.stock_quantity==8


def test_accounting_source_sync_does_not_repeat_automatic_cash_or_zero_credit(db):
    from app.modules.accounting.service import AccountingService
    actor,_,svc,_,_,_,_,task=kitchen(db);deliver(svc,task,actor)
    billing=BillingServiceManager(db);invoice=billing.get_invoice(task.billing_invoice_id,actor)
    # An unpaid credit has no cash movement, so source sync must not post a zero payout.
    billing.create_return(invoice.id,BillingReturnCreate(reason='Unpaid partial service credit',items=[BillingReturnItemCreate(invoice_item_id=invoice.items[0].id,quantity=Decimal('.5'))]),actor,{})
    billing.create_payment(invoice.id,BillingPaymentCreate(amount=75,payment_method='cash'),actor,{})
    before=db.scalar(select(func.count()).select_from(JournalEntry));AccountingService(db).sync_source_entries(actor,{})
    assert db.scalar(select(func.count()).select_from(JournalEntry))==before
    assert balance(db,actor,'1100')==0 and balance(db,actor,'1001')==75


def test_concurrent_preparation_consumes_only_once(database):
    from test_specialist_workflows import isolated_race_database
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    with isolated_race_database(database) as isolated:
        with Session(isolated,expire_on_commit=False,autoflush=False) as session:
            actor,_,_,item,_,_,_,task=kitchen(session);session.commit();ids=(actor.id,item.id,task.id)
        ready=Barrier(2)
        def prepare(_):
            with Session(isolated,expire_on_commit=False,autoflush=False) as session:
                actor=session.get(User,ids[0]);ready.wait(timeout=10)
                try:
                    CateringService(session).update_meal_status(ids[2],CateringMealStatusUpdate(preparation_status='preparing'),actor,{})
                    return 200
                except AppException as error:session.rollback();return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(prepare,range(2)))
        assert sorted(results)==[200,409]
        with Session(isolated) as session:
            assert session.get(InventoryItem,ids[1]).stock_quantity==8
            assert session.scalar(select(func.count()).select_from(InventoryStockTransaction))==1


def test_receiving_posts_inventory_value_and_rejects_foreign_branch_item(db):
    from app.modules.inventory.service import InventoryService
    from app.schemas.inventory import StockReceivingCreate
    from app.models.branch import Branch
    actor,_,_,_=seed(db);svc=InventoryService(db)
    item=InventoryItem(branch_id=actor.branch_id,name='Received ingredient',is_batch_tracked=False,stock_quantity=0,stock_value=0);store=InventoryStore(branch_id=actor.branch_id,code='KITCHEN',name='Kitchen');db.add_all([item,store]);db.commit()
    receipt=svc.create_receiving(StockReceivingCreate(item_id=item.id,store_id=store.id,received_date=date.today(),quantity=2,unit_cost=10,total_cost=20),actor,{})
    assert item.stock_quantity==2 and balance(db,actor,'1300')==20 and balance(db,actor,'2400')==20
    assert db.scalar(select(OperationalPosting).where(OperationalPosting.source_id==receipt.id)).amount==20
    other=Branch(code='FOREIGN',name='Foreign');db.add(other);db.flush();item.branch_id=other.id;db.commit()
    with pytest.raises(AppException):svc.create_receiving(StockReceivingCreate(item_id=item.id,store_id=store.id,received_date=date.today(),quantity=1,unit_cost=10,total_cost=10),actor,{})


def test_zero_payroll_has_approval_evidence_without_fake_cash(db):
    actor,reviewer,svc,employee=payroll_setup(db)
    svc.upsert_salary(HRSalaryStructureCreate(employee_id=employee.id,effective_from=date(2026,2,1),basic_salary=0),actor)
    run=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    svc.approve_payroll(run.id,reviewer,status='approved');svc.approve_payroll(run.id,reviewer,status='paid')
    assert run.total_net_salary==0 and run.status=='paid'
    assert db.scalar(select(func.count()).select_from(JournalEntry))==0
    assert db.scalar(select(func.count()).select_from(OperationalPosting).where(OperationalPosting.source_id==run.id))==2


def test_invoice_discount_and_void_reverse_receivable_without_restock(db):
    from app.modules.billing.operations import BillingOperations
    from app.schemas.billing import BillingInvoiceAmend
    from app.schemas.billing import BillingInvoiceVoidRequest
    actor,_,svc,item,_,_,_,task=kitchen(db);deliver(svc,task,actor)
    operations=BillingOperations(db)
    operations.amend(task.billing_invoice_id,BillingInvoiceAmend(discount_percentage=10,reason='Synthetic approved discount'),actor)
    assert balance(db,actor,'1100')==135
    BillingServiceManager(db).void_invoice(task.billing_invoice_id,BillingInvoiceVoidRequest(reason='Synthetic void after discount'),actor,{})
    assert balance(db,actor,'1100')==0 and item.stock_quantity==8


def test_cancelled_unprepared_recipes_are_not_reported_as_consumed_stock(db):
    actor,patient,svc,item,_,_,_,task=kitchen(db)
    npo=next(x for x in svc.list_diet_types(actor) if x.code=='NPO')
    svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=npo.id,start_at=datetime.now(UTC)-timedelta(days=1)),actor,{})
    assert task.delivery_status=='cancelled' and task.inventory_status=='not_issued'
    assert item.stock_quantity==10 and svc.reports(actor,'stock_usage',{}).rows==[]


def test_physical_stock_report_honors_meal_date_and_ward_filters(db):
    actor,_,svc,_,_,_,_,task=kitchen(db)
    svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),actor,{})
    assert len(svc.reports(actor,'stock_usage',{'meal_date':task.meal_date}).rows)==1
    assert svc.reports(actor,'stock_usage',{'meal_date':task.meal_date+timedelta(days=1)}).rows==[]
    assert svc.reports(actor,'stock_usage',{'ward':'Unrelated ward'}).rows==[]
