from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.catering.service import CateringService
from app.schemas.catering import (
    CateringDashboardRead,
    CateringDietOrderCreate,
    CateringDietOrderRead,
    CateringDietOrderUpdate,
    CateringDietTypeCreate,
    CateringDietTypeRead,
    CateringMealGenerateRequest,
    CateringMealPlanCreate,
    CateringMealPlanRead,
    CateringMealScheduleCreate,
    CateringMealScheduleRead,
    CateringMealStatusUpdate,
    CateringMealTaskRead,
    CateringReportRead,
    CateringSettingCreate,
    CateringSettingRead,
    CateringStaffMealCreate,
    CateringStaffMealRead,
)

router = APIRouter(prefix="/catering", tags=["Catering"])


def diet_order_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}".strip() if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    data["diet_type_name"] = item.diet_type.name if item.diet_type else ""
    data["meal_plan_name"] = item.meal_plan.name if item.meal_plan else None
    data["ordered_by_name"] = item.ordered_by.full_name if item.ordered_by else None
    data["approved_by_name"] = item.approved_by.full_name if item.approved_by else None
    return data


def meal_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}".strip() if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    data["prepared_by_name"] = item.prepared_by.full_name if item.prepared_by else None
    data["delivered_by_name"] = item.delivered_by.full_name if item.delivered_by else None
    data["safety_warnings"] = item.safety_warnings or []
    return data


def meal_plan_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["diet_type_name"] = item.diet_type.name if item.diet_type else None
    return data


def staff_meal_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["department_name"] = item.department.name if item.department else None
    return data


@router.get("/dashboard", response_model=CateringDashboardRead, dependencies=[Depends(require_permissions("catering.dashboard.view"))])
def dashboard(
    meal_date: date | None = None,
    meal_type: str | None = None,
    ward: str | None = None,
    bed: str | None = None,
    diet_type: str | None = None,
    kitchen_status: str | None = None,
    delivery_status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CateringDashboardRead:
    return CateringService(db).dashboard(user, {k: v for k, v in locals().items() if k not in {"user", "db"} and v is not None})


@router.get("/diet-types", response_model=list[CateringDietTypeRead], dependencies=[Depends(require_permissions("catering.view"))])
def list_diet_types(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return CateringService(db).list_diet_types(user)


@router.post("/diet-types", response_model=CateringDietTypeRead, dependencies=[Depends(require_permissions("catering.settings.manage"))])
def create_diet_type(payload: CateringDietTypeCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return CateringService(db).create_diet_type(payload, user, context)


@router.get("/meal-plans", response_model=list[CateringMealPlanRead], dependencies=[Depends(require_permissions("catering.view"))])
def list_meal_plans(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [CateringMealPlanRead.model_validate(meal_plan_payload(item)) for item in CateringService(db).list_meal_plans(user)]


@router.post("/meal-plans", response_model=CateringMealPlanRead, dependencies=[Depends(require_permissions("catering.settings.manage"))])
def create_meal_plan(payload: CateringMealPlanCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).create_meal_plan(payload, user, context)
    return CateringMealPlanRead.model_validate(meal_plan_payload(item))


@router.get("/schedules", response_model=list[CateringMealScheduleRead], dependencies=[Depends(require_permissions("catering.view"))])
def list_schedules(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return CateringService(db).list_schedules(user)


@router.post("/schedules", response_model=CateringMealScheduleRead, dependencies=[Depends(require_permissions("catering.settings.manage"))])
def upsert_schedule(payload: CateringMealScheduleCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return CateringService(db).upsert_schedule(payload, user, context)


@router.get("/diet-orders", response_model=list[CateringDietOrderRead], dependencies=[Depends(require_permissions("catering.view"))])
def list_diet_orders(patient_id: UUID | None = None, active_only: bool = False, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [CateringDietOrderRead.model_validate(diet_order_payload(item)) for item in CateringService(db).list_diet_orders(user, active_only=active_only, patient_id=patient_id)]


@router.post("/diet-orders", response_model=CateringDietOrderRead, dependencies=[Depends(require_any_permissions("catering.diet_order.create", "catering.diet_order.edit"))])
def create_diet_order(payload: CateringDietOrderCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).create_diet_order(payload, user, context)
    return CateringDietOrderRead.model_validate(diet_order_payload(item))


@router.put("/diet-orders/{order_id}", response_model=CateringDietOrderRead, dependencies=[Depends(require_permissions("catering.diet_order.edit"))])
def update_diet_order(order_id: UUID, payload: CateringDietOrderUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).update_diet_order(order_id, payload, user, context)
    return CateringDietOrderRead.model_validate(diet_order_payload(item))


@router.post("/diet-orders/{order_id}/approve", response_model=CateringDietOrderRead, dependencies=[Depends(require_permissions("catering.diet_order.approve"))])
def approve_diet_order(order_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).approve_diet_order(order_id, user, context)
    return CateringDietOrderRead.model_validate(diet_order_payload(item))


@router.post("/meals/generate", response_model=list[CateringMealTaskRead], dependencies=[Depends(require_permissions("catering.meal.prepare"))])
def generate_meals(payload: CateringMealGenerateRequest, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [CateringMealTaskRead.model_validate(meal_payload(item)) for item in CateringService(db).generate_meals(payload, user, context)]


@router.get("/meals", response_model=list[CateringMealTaskRead], dependencies=[Depends(require_permissions("catering.kitchen_queue.view"))])
def list_meals(
    meal_date: date | None = None,
    meal_type: str | None = None,
    ward: str | None = None,
    bed: str | None = None,
    diet_type: str | None = None,
    kitchen_status: str | None = None,
    delivery_status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db", "meal_date"} and v is not None}
    return [CateringMealTaskRead.model_validate(meal_payload(item)) for item in CateringService(db).list_meals(user, meal_date=meal_date, filters=filters)]


@router.patch("/meals/{task_id}/status", response_model=CateringMealTaskRead, dependencies=[Depends(require_any_permissions("catering.meal.prepare", "catering.meal.deliver", "catering.meal.cancel"))])
def update_meal_status(task_id: UUID, payload: CateringMealStatusUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).update_meal_status(task_id, payload, user, context)
    return CateringMealTaskRead.model_validate(meal_payload(item))


@router.get("/staff-meals", response_model=list[CateringStaffMealRead], dependencies=[Depends(require_permissions("catering.staff_meal.manage"))])
def list_staff_meals(meal_date: date | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [CateringStaffMealRead.model_validate(staff_meal_payload(item)) for item in CateringService(db).list_staff_meals(user, meal_date)]


@router.post("/staff-meals", response_model=CateringStaffMealRead, dependencies=[Depends(require_permissions("catering.staff_meal.manage"))])
def create_staff_meal(payload: CateringStaffMealCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).create_staff_meal(payload, user, context)
    return CateringStaffMealRead.model_validate(staff_meal_payload(item))


@router.patch("/staff-meals/{order_id}/{status}", response_model=CateringStaffMealRead, dependencies=[Depends(require_permissions("catering.staff_meal.manage"))])
def update_staff_meal_status(order_id: UUID, status: str, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = CateringService(db).update_staff_meal_status(order_id, status, user, context)
    return CateringStaffMealRead.model_validate(staff_meal_payload(item))


@router.get("/settings", response_model=list[CateringSettingRead], dependencies=[Depends(require_permissions("catering.settings.manage"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return CateringService(db).list_settings(user)


@router.post("/settings", response_model=CateringSettingRead, dependencies=[Depends(require_permissions("catering.settings.manage"))])
def upsert_setting(payload: CateringSettingCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return CateringService(db).upsert_setting(payload, user, context)


@router.get("/reports", response_model=CateringReportRead, dependencies=[Depends(require_permissions("catering.report.view"))])
def reports(
    report_type: str = Query("daily"),
    meal_date: date | None = None,
    ward: str | None = None,
    diet_type: str | None = None,
    meal_type: str | None = None,
    kitchen_status: str | None = None,
    delivery_status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CateringReportRead:
    filters = {k: v for k, v in locals().items() if k not in {"user", "db", "report_type"} and v is not None}
    return CateringService(db).reports(user, report_type, filters)
