"""Support-service money, actor scope, safety and lifecycle regression checks."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from test_opd_workflow_integration import database, db, seed
from app.core.exceptions import AppException
from app.models.branch import Branch
from app.models.hr import HRLeaveType, HRLeaveRequest, HREmployeeLoan
from app.models.user import User
from app.modules.hr.service import HRService, serialize_employee
from app.modules.transport.service import TransportService
from app.modules.catering.service import CateringService
from app.schemas.hr import HREmployeeCreate, HRSalaryStructureCreate, HRPayrollRunCreate, HRLoanCreate
from app.schemas.transport import TransportVehicleCreate, TransportDriverCreate, TransportRequestCreate, TransportDispatchRequest, TransportTripStatusUpdate
from app.schemas.catering import CateringDietOrderCreate, CateringMealGenerateRequest, CateringMealStatusUpdate, CateringStaffMealCreate


def employee(db, actor):
    return HRService(db).create_employee(HREmployeeCreate(full_name='Synthetic employee', joining_date=date(2026,1,1)), actor)


def test_payroll_caps_balance_clips_leave_and_separates_review(db):
    actor,_,_,_=seed(db);svc=HRService(db);e=employee(db,actor)
    svc.upsert_salary(HRSalaryStructureCreate(employee_id=e.id,basic_salary=26000,effective_from=date(2026,1,1)),actor)
    lt=HRLeaveType(branch_id=actor.branch_id,code='UNPAID',name='Unpaid',is_paid=False);db.add(lt);db.flush()
    db.add(HRLeaveRequest(branch_id=actor.branch_id,employee_id=e.id,leave_type_id=lt.id,start_date=date(2026,9,30),end_date=date(2026,10,2),number_of_days=3,status='approved'))
    loan=svc.create_loan(HRLoanCreate(employee_id=e.id,approved_amount=300,monthly_installment=500,deduction_start_month='2026-10'),actor)
    run=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    assert run.items[0].unpaid_leave_days==2 and run.items[0].loan_deduction==300
    assert run.total_net_salary==23700
    with pytest.raises(AppException):svc.approve_payroll(run.id,actor,status='approved')
    reviewer=User(branch_id=actor.branch_id,username='reviewer',email='reviewer@example.test',full_name='Reviewer',hashed_password='unused');db.add(reviewer);db.flush()
    svc.approve_payroll(run.id,reviewer,status='approved');svc.approve_payroll(run.id,reviewer,status='paid')
    svc.approve_payroll(run.id,reviewer,status='paid')
    assert loan.remaining_balance==0 and run.approved_by_user_id==reviewer.id
    svc.approve_payroll(run.id,reviewer,status='locked')
    with pytest.raises(AppException):svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)


def test_employee_self_scope_and_attendance_cross_branch(db):
    actor,_,_,_=seed(db);svc=HRService(db);e=employee(db,actor)
    user=User(branch_id=actor.branch_id,username='employee',email='employee@example.test',full_name='Employee',hashed_password='unused');db.add(user);db.flush();e.user_id=user.id
    other=employee(db,actor);other.bank_account_number='sensitive';db.commit()
    assert [x.id for x in svc.list_employees(user,page=1,page_size=100)[0]]==[e.id]
    assert serialize_employee(other,user)['bank_account_number'] is None
    from app.models.hr import HREmployeeDocument
    transport=User(branch_id=actor.branch_id,username='transport',email='transport@example.test',full_name='Transport',hashed_password='unused',direct_permissions=[p for p in actor.direct_permissions if p.code in {'hr.view','transport.driver.manage'}]);db.add(transport)
    db.add(HREmployeeDocument(employee_id=other.id,document_type='nid',file_url='https://example.test/private-document'));db.flush()
    assert svc.list_employees(transport,page=1,page_size=100)[1]==2
    assert svc.list_documents(transport)==[] and svc.dashboard(transport).total_employees==0
    with pytest.raises(AppException):svc._get_employee(other.id,user)
    branch=Branch(code='OTHER',name='Other');db.add(branch);db.flush();actor.branch_id=branch.id
    with pytest.raises(AppException):svc._get_employee(e.id,actor)


def transport_case(db):
    actor,_,patient,_=seed(db);svc=TransportService(db)
    vehicle=svc.create_vehicle(TransportVehicleCreate(vehicle_number='V-'+uuid4().hex[:8],vehicle_type='car'),actor,{})
    driver_employee=employee(db,actor)
    driver=svc.create_driver(TransportDriverCreate(employee_id=driver_employee.id,driver_name='Synthetic driver',license_number=uuid4().hex),actor,{})
    request=svc.create_request(TransportRequestCreate(patient_id=patient.id,request_type='Patient',pickup_location='Home',dropoff_location='Hospital'),actor,{})
    trip=svc.dispatch(request.id,TransportDispatchRequest(vehicle_id=vehicle.id,driver_id=driver.id),actor,{})
    return actor,svc,request,trip


def test_transport_sequence_duplicate_dispatch_and_closed_trip(db):
    actor,svc,request,trip=transport_case(db)
    with pytest.raises(AppException):svc.dispatch(request.id,TransportDispatchRequest(vehicle_id=trip.vehicle_id,driver_id=trip.driver_id,override=True,override_reason='cannot duplicate'),actor,{})
    with pytest.raises(AppException):svc.update_trip_status(trip.id,TransportTripStatusUpdate(status='completed'),actor,{})
    for status in ['dispatched','arrived_at_pickup','patient_picked_up','in_transit','arrived_at_destination','completed']:
        svc.update_trip_status(trip.id,TransportTripStatusUpdate(status=status),actor,{})
    assert trip.vehicle.current_status=='available' and trip.driver.availability_status=='available'
    with pytest.raises(AppException):svc.update_trip_status(trip.id,TransportTripStatusUpdate(status='dispatched'),actor,{})


def test_transport_denies_other_branch_and_unassigned_actor(db):
    actor,svc,request,trip=transport_case(db)
    unrelated=User(branch_id=actor.branch_id,username='unassigned',email='unassigned@example.test',full_name='Unassigned',hashed_password='unused');db.add(unrelated);db.flush()
    assert svc.list_trips(unrelated)==[]
    with pytest.raises(AppException):svc._get_trip(trip.id,unrelated)
    branch=Branch(code='OTHER',name='Other');db.add(branch);db.flush();actor.branch_id=branch.id
    with pytest.raises(AppException):svc._get_vehicle(trip.vehicle_id,actor)


def test_meal_generation_dates_idempotence_and_delivery_sequence(db):
    actor,_,patient,_=seed(db);svc=CateringService(db);types=svc.list_diet_types(actor);regular=next(x for x in types if x.code=='REGULAR')
    day=date(2026,10,10)
    order=svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=regular.id,start_at=datetime(2026,10,10,6,tzinfo=UTC),end_at=datetime(2026,10,10,15,tzinfo=UTC)),actor,{})
    tasks=svc.generate_meals(CateringMealGenerateRequest(meal_date=day),actor,{})
    assert tasks and all(t.due_at.hour>=6 for t in tasks)
    assert len(svc.generate_meals(CateringMealGenerateRequest(meal_date=day),actor,{}))==0
    assert svc.generate_meals(CateringMealGenerateRequest(meal_date=day-timedelta(days=1)),actor,{})==[]
    task=tasks[0]
    order.end_at=datetime.now(UTC)+timedelta(days=1);db.flush()
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(delivery_status='delivered'),actor,{})
    for status in ['preparing','ready']:svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status=status),actor,{})
    for status in ['out_for_delivery','delivered']:svc.update_meal_status(task.id,CateringMealStatusUpdate(delivery_status=status),actor,{})
    assert task.delivered_at and task.delivered_by_user_id==actor.id
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),actor,{})


def test_catering_all_reads_and_staff_status_branch_scoped(db):
    actor,_,_,_=seed(db);svc=CateringService(db)
    item=svc.create_staff_meal(CateringStaffMealCreate(staff_name='Synthetic staff',meal_date=date.today(),meal_type='lunch'),actor,{})
    with pytest.raises(AppException):svc.update_staff_meal_status(item.id,'served',actor,{})
    svc.update_staff_meal_status(item.id,'issued',actor,{});svc.update_staff_meal_status(item.id,'served',actor,{})
    branch=Branch(code='OTHER',name='Other');db.add(branch);db.flush();actor.branch_id=branch.id
    assert svc.list_staff_meals(actor)==[] and svc.list_meals(actor)==[] and svc.reports(actor,'stock_usage',{}).rows==[]
    with pytest.raises(AppException):svc.update_staff_meal_status(item.id,'cancelled',actor,{})


def test_blank_employee_email_is_nullable_and_account_is_unique(db):
    actor,_,_,_=seed(db);svc=HRService(db)
    first=svc.create_employee(HREmployeeCreate(full_name='First staff',email='',joining_date=date(2026,1,1)),actor)
    second=svc.create_employee(HREmployeeCreate(full_name='Second staff',email='  ',joining_date=date(2026,1,1)),actor)
    assert first.email is None and second.email is None and first.staff_code!=second.staff_code


def test_paid_leave_does_not_deduct_and_future_salary_is_not_used(db):
    from app.schemas.hr import HRAttendanceCreate
    actor,_,_,_=seed(db);svc=HRService(db);e=employee(db,actor)
    svc.upsert_salary(HRSalaryStructureCreate(employee_id=e.id,basic_salary=26000,effective_from=date(2026,10,1)),actor)
    lt=HRLeaveType(branch_id=actor.branch_id,code='PAID',name='Paid leave',is_paid=True);db.add(lt);db.flush()
    db.add(HRLeaveRequest(branch_id=actor.branch_id,employee_id=e.id,leave_type_id=lt.id,start_date=date(2026,10,2),end_date=date(2026,10,2),number_of_days=1,status='approved'));db.flush()
    svc.mark_attendance(HRAttendanceCreate(employee_id=e.id,attendance_date=date(2026,10,2),status='on_leave'),actor)
    with pytest.raises(AppException):svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-09'),actor)
    # An API request rollback discards the rejected empty run; direct service callers explicitly roll back.
    db.query(__import__('app.models.hr',fromlist=['HRPayrollRun']).HRPayrollRun).filter_by(payroll_month='2026-09').delete()
    run=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    assert run.items[0].unpaid_leave_days==0 and run.total_net_salary==26000


def test_overtime_requires_independent_review_before_payroll(db):
    from app.schemas.hr import HROvertimeCreate
    actor,_,_,_=seed(db);svc=HRService(db);e=employee(db,actor)
    item=svc.create_overtime(HROvertimeCreate(employee_id=e.id,overtime_date=date(2026,10,3),overtime_hours=2),actor)
    with pytest.raises(AppException):svc.decide_overtime(item.id,actor,'approved')
    reviewer=User(branch_id=actor.branch_id,username='reviewer',email='reviewer@example.test',full_name='Reviewer',hashed_password='unused',direct_permissions=actor.direct_permissions);db.add(reviewer);db.flush()
    svc.decide_overtime(item.id,reviewer,'approved')
    assert item.status=='approved' and item.approved_by_user_id==reviewer.id
    with pytest.raises(AppException):svc.decide_overtime(item.id,reviewer,'rejected')


def test_maintenance_closes_and_restores_vehicle_once_all_records_close(db):
    from app.schemas.transport import TransportMaintenanceCreate
    actor,svc,request,trip=transport_case(db)
    for status in ['dispatched','arrived_at_pickup','patient_picked_up','in_transit','arrived_at_destination','completed']:svc.update_trip_status(trip.id,TransportTripStatusUpdate(status=status),actor,{})
    items=[svc.create_maintenance(TransportMaintenanceCreate(vehicle_id=trip.vehicle_id,maintenance_type='Inspection',service_date=date.today(),status='scheduled'),actor,{}) for _ in range(2)]
    svc.complete_maintenance(items[0].id,actor,{})
    assert trip.vehicle.current_status=='under_maintenance'
    svc.complete_maintenance(items[1].id,actor,{})
    assert trip.vehicle.current_status=='available'
    svc.complete_maintenance(items[1].id,actor,{})


def test_kitchen_cannot_authorize_allergy_override_but_diet_approver_can(db):
    from app.models.catering import CateringMealPlan
    actor,_,patient,_=seed(db);svc=CateringService(db);regular=next(x for x in svc.list_diet_types(actor) if x.code=='REGULAR')
    plan=CateringMealPlan(branch_id=actor.branch_id,diet_type_id=regular.id,name='Synthetic plan',meal_type='lunch',allergens='milk');db.add(plan);db.flush()
    order=svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=regular.id,meal_plan_id=plan.id,allergies='milk',start_at=datetime(2026,10,1,tzinfo=UTC)),actor,{})
    task=svc.generate_meals(CateringMealGenerateRequest(meal_date=date(2026,10,10)),actor,{})[0]
    assert task.preparation_status=='on_hold'
    kitchen=User(branch_id=actor.branch_id,username='kitchen',email='kitchen@example.test',full_name='Kitchen',hashed_password='unused',direct_permissions=[p for p in actor.direct_permissions if p.code in {'catering.meal.prepare','catering.meal.deliver'}])
    approver=User(branch_id=actor.branch_id,username='dietitian',email='dietitian@example.test',full_name='Dietitian',hashed_password='unused',direct_permissions=[p for p in actor.direct_permissions if p.code=='catering.diet_order.approve']);db.add_all([kitchen,approver]);db.flush()
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),kitchen,{})
    with pytest.raises(AppException):svc.update_meal_status(task.id,CateringMealStatusUpdate(override_reason='Forbidden'),kitchen,{})
    svc.update_meal_status(task.id,CateringMealStatusUpdate(override_reason='Synthetic reviewed exception only'),approver,{})
    svc.update_meal_status(task.id,CateringMealStatusUpdate(preparation_status='preparing'),kitchen,{})
    assert task.preparation_status=='preparing' and task.override_reason=='Synthetic reviewed exception only'


def test_first_use_catering_defaults_are_persistent_and_concurrency_safe(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from test_specialist_workflows import isolated_race_database
    with isolated_race_database(database) as isolated:
        with Session(isolated,expire_on_commit=False,autoflush=False) as session:
            actor,_,_,_=seed(session);session.commit();actor_id=actor.id
        ready=Barrier(2)
        def load():
            with Session(isolated,expire_on_commit=False,autoflush=False) as session:
                actor=session.get(User,actor_id);ready.wait(timeout=10)
                return {x.code:x.id for x in CateringService(session).list_diet_types(actor)}
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:load(),range(2)))
        assert results[0]==results[1] and len(results[0])==14
        with Session(isolated) as session:
            actor=session.get(User,actor_id);assert {x.code:x.id for x in CateringService(session).list_diet_types(actor)}==results[0]


def test_meal_plan_with_blank_optional_allergens_generates(db):
    from app.models.catering import CateringMealPlan
    actor,_,patient,_=seed(db);svc=CateringService(db);regular=next(x for x in svc.list_diet_types(actor) if x.code=='REGULAR')
    plan=CateringMealPlan(branch_id=actor.branch_id,diet_type_id=regular.id,name='Synthetic optional allergens',meal_type='lunch',allergens=None);db.add(plan);db.flush()
    svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=regular.id,meal_plan_id=plan.id,start_at=datetime(2026,10,1,tzinfo=UTC)),actor,{})
    tasks=svc.generate_meals(CateringMealGenerateRequest(meal_date=date(2026,10,10)),actor,{})
    assert len(tasks)==1 and tasks[0].meal_type=='lunch'


def test_department_and_whole_branch_payroll_cannot_overlap(db):
    from app.models.department import Department
    actor,_,_,_=seed(db);svc=HRService(db)
    departments=[Department(branch_id=actor.branch_id,code='DEP-'+str(i),name='Department '+str(i)) for i in range(2)];db.add_all(departments);db.flush()
    for department in departments:
        e=svc.create_employee(HREmployeeCreate(full_name=department.name,department_id=department.id,joining_date=date(2026,1,1)),actor)
        svc.upsert_salary(HRSalaryStructureCreate(employee_id=e.id,effective_from=date(2026,1,1),basic_salary=1000),actor)
    svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10',department_id=departments[0].id),actor)
    with pytest.raises(AppException):svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10'),actor)
    second=svc.process_payroll(HRPayrollRunCreate(payroll_month='2026-10',department_id=departments[1].id),actor)
    assert second.total_employees==1 and second.total_net_salary==1000


def test_concurrent_dispatch_cannot_share_vehicle_even_with_override(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models.transport import TransportTrip
    from test_specialist_workflows import isolated_race_database
    with isolated_race_database(database) as isolated:
        with Session(isolated,expire_on_commit=False,autoflush=False) as session:
            actor,_,patient,_=seed(session);session.commit();svc=TransportService(session)
            vehicle=svc.create_vehicle(TransportVehicleCreate(vehicle_number='RACE',vehicle_type='car'),actor,{})
            driver=svc.create_driver(TransportDriverCreate(driver_name='Synthetic driver',license_number=uuid4().hex),actor,{})
            requests=[svc.create_request(TransportRequestCreate(patient_id=patient.id,request_type='Patient',pickup_location='Home',dropoff_location='Hospital'),actor,{}) for _ in range(2)];session.commit()
            ids=(actor.id,vehicle.id,driver.id,[r.id for r in requests])
        ready=Barrier(2)
        def dispatch(index):
            with Session(isolated,expire_on_commit=False,autoflush=False) as session:
                actor=session.get(User,ids[0]);ready.wait(timeout=10)
                try:
                    TransportService(session).dispatch(ids[3][index],TransportDispatchRequest(vehicle_id=ids[1],driver_id=ids[2],override=True,override_reason='Cannot bypass active assignment'),actor,{})
                    session.commit();return 200
                except AppException as error:
                    session.rollback();return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(dispatch,range(2)))
        assert sorted(results)==[200,409]
        with Session(isolated) as session:assert len(list(session.scalars(select(TransportTrip))))==1


def test_changed_diet_cannot_bypass_review_and_can_replace_cancelled_tickets(db):
    from app.models.catering import CateringMealPlan
    from app.schemas.catering import CateringDietOrderUpdate
    actor,_,patient,_=seed(db);svc=CateringService(db);types=svc.list_diet_types(actor)
    regular=next(x for x in types if x.code=='REGULAR');diabetic=next(x for x in types if x.code=='DIABETIC')
    plan=CateringMealPlan(branch_id=actor.branch_id,diet_type_id=regular.id,name='Synthetic lunch',meal_type='lunch');db.add(plan);db.flush()
    order=svc.create_diet_order(CateringDietOrderCreate(patient_id=patient.id,diet_type_id=regular.id,meal_plan_id=plan.id,start_at=datetime(2026,10,1,tzinfo=UTC)),actor,{})
    old=svc.generate_meals(CateringMealGenerateRequest(meal_date=date(2026,10,10)),actor,{})[0]
    svc.update_diet_order(order.id,CateringDietOrderUpdate(patient_id=patient.id,diet_type_id=diabetic.id,start_at=datetime(2026,10,1,tzinfo=UTC),requires_approval=False,status='active'),actor,{})
    assert order.status=='pending_approval' and order.approved_by_user_id is None and old.delivery_status=='cancelled'
    assert svc.generate_meals(CateringMealGenerateRequest(meal_date=date(2026,10,10)),actor,{})==[]
    svc.approve_diet_order(order.id,actor,{})
    replacement=svc.generate_meals(CateringMealGenerateRequest(meal_date=date(2026,10,10)),actor,{})
    assert any(t.meal_type=='lunch' and t.id!=old.id for t in replacement)
