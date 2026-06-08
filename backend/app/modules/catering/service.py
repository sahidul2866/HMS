from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.catering import (
    CateringDietOrder,
    CateringDietType,
    CateringInventoryUsage,
    CateringMealPlan,
    CateringMealSchedule,
    CateringMealTask,
    CateringSetting,
    CateringStaffMealOrder,
)
from app.models.encounter import ERVisit, IPDAdmission
from app.models.hr import HREmployee
from app.models.patient import Patient
from app.models.user import User
from app.modules.audit.service import AuditService
from app.schemas.catering import (
    CateringDashboardRead,
    CateringDietOrderCreate,
    CateringDietOrderUpdate,
    CateringDietTypeCreate,
    CateringMealGenerateRequest,
    CateringMealPlanCreate,
    CateringMealScheduleCreate,
    CateringMealStatusUpdate,
    CateringReportRead,
    CateringSettingCreate,
    CateringStaffMealCreate,
)


DEFAULT_DIET_TYPES = [
    ("REGULAR", "Regular diet", False, False, ""),
    ("SOFT", "Soft diet", False, False, "Easy chew"),
    ("LIQUID", "Liquid diet", False, False, "Liquid only"),
    ("DIABETIC", "Diabetic diet", False, True, "No added sugar; carb controlled"),
    ("LOW_SALT", "Low-salt diet", False, True, "Reduced sodium"),
    ("LOW_FAT", "Low-fat diet", False, False, "Low oil and low fat"),
    ("HIGH_PROTEIN", "High-protein diet", False, False, "Protein rich"),
    ("RENAL", "Renal diet", False, True, "Renal restriction"),
    ("CARDIAC", "Cardiac diet", False, True, "Heart healthy; low salt"),
    ("POST_OP", "Post-operative diet", False, True, "Post-operative progression"),
    ("PEDIATRIC", "Pediatric diet", False, False, "Child appropriate portions"),
    ("MATERNITY", "Maternity diet", False, False, "Maternity nutrition"),
    ("NPO", "NPO / nil by mouth", True, True, "No oral intake"),
    ("CUSTOM", "Custom diet", False, True, "Custom restriction"),
]

DEFAULT_SCHEDULES = [
    ("breakfast", "Breakfast", time(8, 0), 1),
    ("morning_snack", "Morning snack", time(10, 30), 2),
    ("lunch", "Lunch", time(13, 0), 3),
    ("evening_snack", "Evening snack", time(16, 30), 4),
    ("dinner", "Dinner", time(20, 0), 5),
    ("late_night", "Late-night meal", time(22, 30), 6),
]


class CateringService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_defaults(self, actor: User | None = None) -> None:
        branch_id = actor.branch_id if actor else None
        for code, name, is_npo, requires_approval, restrictions in DEFAULT_DIET_TYPES:
            existing = self.db.scalar(select(CateringDietType).where(CateringDietType.code == code))
            if not existing:
                self.db.add(
                    CateringDietType(
                        branch_id=branch_id,
                        code=code,
                        name=name,
                        is_npo=is_npo,
                        requires_approval=requires_approval,
                        default_restrictions=restrictions,
                    )
                )
        for meal_type, display_name, serving_time, sort_order in DEFAULT_SCHEDULES:
            existing = self.db.scalar(select(CateringMealSchedule).where(CateringMealSchedule.meal_type == meal_type))
            if not existing:
                self.db.add(
                    CateringMealSchedule(
                        branch_id=branch_id,
                        meal_type=meal_type,
                        display_name=display_name,
                        serving_time=serving_time,
                        sort_order=sort_order,
                    )
                )
        self.db.flush()

    def dashboard(self, actor: User, filters: dict) -> CateringDashboardRead:
        self.ensure_defaults(actor)
        meal_date = filters.get("meal_date") or date.today()
        tasks = self.list_meals(actor, meal_date=meal_date, filters=filters)
        active_orders = self.list_diet_orders(actor, active_only=True)
        by_ward: dict[str, int] = {}
        by_diet_type: dict[str, int] = {}
        by_meal_type: dict[str, int] = {}
        now = datetime.now(UTC)
        for task in tasks:
            by_ward[task.ward_name or "Unassigned"] = by_ward.get(task.ward_name or "Unassigned", 0) + 1
            by_diet_type[task.diet_type_name] = by_diet_type.get(task.diet_type_name, 0) + 1
            by_meal_type[task.meal_type] = by_meal_type.get(task.meal_type, 0) + 1
        return CateringDashboardRead(
            total_meals_today=len(tasks),
            pending_meal_orders=len([item for item in tasks if item.preparation_status in {"scheduled", "sent_to_kitchen", "on_hold"}]),
            under_preparation=len([item for item in tasks if item.preparation_status == "preparing"]),
            ready_for_delivery=len([item for item in tasks if item.preparation_status == "ready"]),
            delivered=len([item for item in tasks if item.delivery_status == "delivered"]),
            special_diet_patients=len({item.patient_id for item in active_orders if item.requires_approval or item.diet_type.requires_approval}),
            npo_patients=len({item.patient_id for item in active_orders if item.diet_type.is_npo}),
            allergy_risk_patients=len({item.patient_id for item in active_orders if (item.allergies or "").strip()}),
            missed_or_delayed=len([item for item in tasks if item.preparation_status == "missed" or (item.delivery_status != "delivered" and item.due_at < now)]),
            stock_shortages=len([item for item in tasks if item.inventory_status == "shortage"]),
            by_ward=by_ward,
            by_diet_type=by_diet_type,
            by_meal_type=by_meal_type,
        )

    def list_diet_types(self, actor: User) -> list[CateringDietType]:
        self.ensure_defaults(actor)
        return list(self.db.scalars(select(CateringDietType).where(CateringDietType.is_active.is_(True)).order_by(CateringDietType.name.asc())))

    def create_diet_type(self, payload: CateringDietTypeCreate, actor: User, context: dict[str, str | None]) -> CateringDietType:
        existing = self.db.scalar(select(CateringDietType).where(func.lower(CateringDietType.code) == payload.code.lower()))
        if existing:
            raise AppException(409, "diet_type_exists", "Diet type already exists")
        item = CateringDietType(branch_id=actor.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "catering.diet_type.create", "catering_diet_type", item, payload.model_dump(), context)
        return item

    def list_meal_plans(self, actor: User) -> list[CateringMealPlan]:
        self.ensure_defaults(actor)
        stmt = select(CateringMealPlan).options(joinedload(CateringMealPlan.diet_type)).where(CateringMealPlan.is_active.is_(True)).order_by(CateringMealPlan.name.asc())
        return list(self.db.scalars(stmt).unique())

    def create_meal_plan(self, payload: CateringMealPlanCreate, actor: User, context: dict[str, str | None]) -> CateringMealPlan:
        item = CateringMealPlan(branch_id=actor.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "catering.meal_plan.create", "catering_meal_plan", item, payload.model_dump(mode="json"), context)
        return item

    def list_schedules(self, actor: User) -> list[CateringMealSchedule]:
        self.ensure_defaults(actor)
        return list(self.db.scalars(select(CateringMealSchedule).where(CateringMealSchedule.is_active.is_(True)).order_by(CateringMealSchedule.sort_order.asc())))

    def upsert_schedule(self, payload: CateringMealScheduleCreate, actor: User, context: dict[str, str | None]) -> CateringMealSchedule:
        item = self.db.scalar(select(CateringMealSchedule).where(CateringMealSchedule.meal_type == payload.meal_type))
        if not item:
            item = CateringMealSchedule(branch_id=actor.branch_id, created_by=actor.id)
            self.db.add(item)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.updated_by = actor.id
        self._audit(actor, "catering.schedule.upsert", "catering_meal_schedule", item, payload.model_dump(mode="json"), context)
        return item

    def list_diet_orders(self, actor: User, *, active_only: bool = False, patient_id=None) -> list[CateringDietOrder]:
        stmt = (
            select(CateringDietOrder)
            .options(
                joinedload(CateringDietOrder.patient),
                joinedload(CateringDietOrder.diet_type),
                joinedload(CateringDietOrder.meal_plan),
                joinedload(CateringDietOrder.ordered_by),
                joinedload(CateringDietOrder.approved_by),
            )
            .where(CateringDietOrder.is_active.is_(True))
            .order_by(CateringDietOrder.created_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(or_(CateringDietOrder.branch_id == actor.branch_id, CateringDietOrder.branch_id.is_(None)))
        if active_only:
            now = datetime.now(UTC)
            stmt = stmt.where(CateringDietOrder.status.in_(["active", "pending_approval"]), CateringDietOrder.start_at <= now, or_(CateringDietOrder.end_at.is_(None), CateringDietOrder.end_at >= now))
        if patient_id:
            stmt = stmt.where(CateringDietOrder.patient_id == patient_id)
        return list(self.db.scalars(stmt).unique())

    def create_diet_order(self, payload: CateringDietOrderCreate, actor: User, context: dict[str, str | None]) -> CateringDietOrder:
        patient = self.db.get(Patient, payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        diet_type = self.db.get(CateringDietType, payload.diet_type_id)
        if not diet_type:
            raise AppException(404, "diet_type_not_found", "Diet type not found")
        if payload.ipd_admission_id:
            admission = self.db.get(IPDAdmission, payload.ipd_admission_id)
            if admission:
                payload.ward_name = payload.ward_name or admission.ward_name
                payload.bed_number = payload.bed_number or admission.bed_number
                payload.admission_number = payload.admission_number or admission.admission_number
        if payload.er_visit_id:
            visit = self.db.get(ERVisit, payload.er_visit_id)
            if visit:
                payload.admission_number = payload.admission_number or visit.visit_number
                payload.ward_name = payload.ward_name or visit.assigned_location
        requires_approval = diet_type.requires_approval if payload.requires_approval is None else payload.requires_approval
        order_data = payload.model_dump(exclude={"requires_approval"})
        order_data["restrictions"] = payload.restrictions or diet_type.default_restrictions
        order = CateringDietOrder(
            branch_id=actor.branch_id or patient.branch_id,
            **order_data,
            status="pending_approval" if requires_approval else "active",
            ordered_by_user_id=actor.id,
            approved_by_user_id=None if requires_approval else actor.id,
            approved_at=None if requires_approval else datetime.now(UTC),
            requires_approval=requires_approval,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(order)
        self._audit(actor, "catering.diet_order.create", "catering_diet_order", order, payload.model_dump(mode="json"), context)
        return order

    def update_diet_order(self, order_id, payload: CateringDietOrderUpdate, actor: User, context: dict[str, str | None]) -> CateringDietOrder:
        order = self.db.get(CateringDietOrder, order_id)
        if not order:
            raise AppException(404, "diet_order_not_found", "Diet order not found")
        for key, value in payload.model_dump(exclude={"requires_approval"}).items():
            setattr(order, key, value)
        order.updated_by = actor.id
        self._audit(actor, "catering.diet_order.update", "catering_diet_order", order, payload.model_dump(mode="json"), context)
        return order

    def approve_diet_order(self, order_id, actor: User, context: dict[str, str | None]) -> CateringDietOrder:
        order = self.db.get(CateringDietOrder, order_id)
        if not order:
            raise AppException(404, "diet_order_not_found", "Diet order not found")
        order.status = "active"
        order.approved_by_user_id = actor.id
        order.approved_at = datetime.now(UTC)
        order.updated_by = actor.id
        self._audit(actor, "catering.diet_order.approve", "catering_diet_order", order, {}, context)
        return order

    def generate_meals(self, payload: CateringMealGenerateRequest, actor: User, context: dict[str, str | None]) -> list[CateringMealTask]:
        self.ensure_defaults(actor)
        schedules = self.list_schedules(actor)
        orders = self.list_diet_orders(actor, active_only=True)
        created: list[CateringMealTask] = []
        for order in orders:
            if order.diet_type.is_npo:
                continue
            for schedule in schedules:
                if order.meal_plan and order.meal_plan.meal_type != schedule.meal_type:
                    continue
                due_at = datetime.combine(payload.meal_date, schedule.serving_time).replace(tzinfo=UTC)
                existing = self.db.scalar(
                    select(CateringMealTask).where(
                        CateringMealTask.diet_order_id == order.id,
                        CateringMealTask.meal_date == payload.meal_date,
                        CateringMealTask.meal_type == schedule.meal_type,
                    )
                )
                if existing:
                    continue
                warnings = self._safety_warnings(order)
                meal_plan = order.meal_plan
                count = int(self.db.scalar(select(func.count(CateringMealTask.id))) or 0) + len(created) + 1
                task = CateringMealTask(
                    branch_id=order.branch_id,
                    diet_order_id=order.id,
                    patient_id=order.patient_id,
                    meal_plan_id=meal_plan.id if meal_plan else None,
                    meal_number=f"MEAL-{payload.meal_date.strftime('%Y%m%d')}-{count:04d}",
                    meal_date=payload.meal_date,
                    meal_type=schedule.meal_type,
                    due_at=due_at,
                    ward_name=order.ward_name,
                    bed_number=order.bed_number,
                    diet_type_name=order.diet_type.name,
                    restrictions=order.restrictions,
                    allergies=order.allergies,
                    special_instructions=order.special_instructions,
                    preparation_status="on_hold" if warnings else "scheduled",
                    delivery_status="pending",
                    safety_status="warning" if warnings else "clear",
                    safety_warnings=warnings,
                    billable_amount=meal_plan.billable_amount if meal_plan else Decimal("0"),
                    inventory_status=self._inventory_status(meal_plan),
                    ticket_code=f"CATER-{payload.meal_date.strftime('%Y%m%d')}-{count:04d}",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(task)
                created.append(task)
                if meal_plan and meal_plan.inventory_item:
                    self.db.add(CateringInventoryUsage(branch_id=order.branch_id, meal_task=task, inventory_item=meal_plan.inventory_item, item_name=meal_plan.inventory_item.name, quantity_used=meal_plan.inventory_quantity, unit=meal_plan.inventory_item.unit_of_measurement, stock_status=task.inventory_status or "recorded", created_by=actor.id, updated_by=actor.id))
        self._audit(actor, "catering.meals.generate", "catering_meal_task", None, {"meal_date": str(payload.meal_date), "created": len(created)}, context)
        return created

    def list_meals(self, actor: User, *, meal_date: date | None = None, filters: dict | None = None) -> list[CateringMealTask]:
        filters = filters or {}
        stmt = (
            select(CateringMealTask)
            .options(joinedload(CateringMealTask.patient), joinedload(CateringMealTask.meal_plan), joinedload(CateringMealTask.prepared_by), joinedload(CateringMealTask.delivered_by))
            .where(CateringMealTask.is_active.is_(True))
            .order_by(CateringMealTask.due_at.asc())
        )
        if meal_date:
            stmt = stmt.where(CateringMealTask.meal_date == meal_date)
        if filters.get("meal_type"):
            stmt = stmt.where(CateringMealTask.meal_type == filters["meal_type"])
        if filters.get("ward"):
            stmt = stmt.where(func.lower(func.coalesce(CateringMealTask.ward_name, "")).like(f"%{filters['ward'].lower()}%"))
        if filters.get("bed"):
            stmt = stmt.where(func.lower(func.coalesce(CateringMealTask.bed_number, "")).like(f"%{filters['bed'].lower()}%"))
        if filters.get("diet_type"):
            stmt = stmt.where(func.lower(CateringMealTask.diet_type_name).like(f"%{filters['diet_type'].lower()}%"))
        if filters.get("kitchen_status"):
            stmt = stmt.where(CateringMealTask.preparation_status == filters["kitchen_status"])
        if filters.get("delivery_status"):
            stmt = stmt.where(CateringMealTask.delivery_status == filters["delivery_status"])
        return list(self.db.scalars(stmt).unique())

    def update_meal_status(self, task_id, payload: CateringMealStatusUpdate, actor: User, context: dict[str, str | None]) -> CateringMealTask:
        task = self.db.get(CateringMealTask, task_id)
        if not task:
            raise AppException(404, "meal_not_found", "Meal task not found")
        if task.safety_warnings and payload.preparation_status in {"preparing", "ready"} and not (payload.override_reason or task.override_reason):
            raise AppException(409, "safety_override_required", "Safety warning requires authorized override reason")
        now = datetime.now(UTC)
        if payload.preparation_status:
            task.preparation_status = payload.preparation_status
            if payload.preparation_status == "preparing":
                task.prepared_by_user_id = actor.id
            if payload.preparation_status == "ready":
                task.prepared_by_user_id = actor.id
                task.prepared_at = now
        if payload.delivery_status:
            task.delivery_status = payload.delivery_status
            if payload.delivery_status == "out_for_delivery":
                task.preparation_status = "out_for_delivery"
            if payload.delivery_status == "delivered":
                task.preparation_status = "delivered"
                task.delivered_by_user_id = actor.id
                task.delivered_at = now
            if payload.delivery_status in {"refused", "missed", "cancelled"}:
                task.preparation_status = payload.delivery_status
        for key in ("received_by", "patient_response", "refusal_reason", "remarks", "override_reason"):
            value = getattr(payload, key)
            if value is not None:
                setattr(task, key, value)
        if payload.override_reason:
            task.safety_status = "overridden"
        task.updated_by = actor.id
        self._audit(actor, "catering.meal.status", "catering_meal_task", task, payload.model_dump(), context)
        return task

    def create_staff_meal(self, payload: CateringStaffMealCreate, actor: User, context: dict[str, str | None]) -> CateringStaffMealOrder:
        employee = self.db.get(HREmployee, payload.employee_id) if payload.employee_id else None
        if not employee and not payload.staff_name:
            raise AppException(422, "staff_name_required", "Staff name is required when no employee is selected")
        count = int(self.db.scalar(select(func.count(CateringStaffMealOrder.id))) or 0) + 1
        order_data = payload.model_dump()
        order_data["staff_name"] = employee.full_name if employee else payload.staff_name
        order_data["staff_code"] = employee.staff_code if employee else payload.staff_code
        order_data["department_id"] = employee.department_id if employee else payload.department_id
        item = CateringStaffMealOrder(
            branch_id=actor.branch_id,
            **order_data,
            token_code=f"STAFF-MEAL-{date.today().strftime('%Y%m%d')}-{count:04d}",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(item)
        self._audit(actor, "catering.staff_meal.create", "catering_staff_meal", item, payload.model_dump(mode="json"), context)
        return item

    def list_staff_meals(self, actor: User, meal_date: date | None = None) -> list[CateringStaffMealOrder]:
        stmt = select(CateringStaffMealOrder).options(joinedload(CateringStaffMealOrder.department), joinedload(CateringStaffMealOrder.employee)).where(CateringStaffMealOrder.is_active.is_(True)).order_by(CateringStaffMealOrder.created_at.desc())
        if meal_date:
            stmt = stmt.where(CateringStaffMealOrder.meal_date == meal_date)
        return list(self.db.scalars(stmt).unique())

    def update_staff_meal_status(self, order_id, status: str, actor: User, context: dict[str, str | None]) -> CateringStaffMealOrder:
        item = self.db.get(CateringStaffMealOrder, order_id)
        if not item:
            raise AppException(404, "staff_meal_not_found", "Staff meal not found")
        item.status = status
        item.updated_by = actor.id
        self._audit(actor, "catering.staff_meal.status", "catering_staff_meal", item, {"status": status}, context)
        return item

    def list_settings(self, actor: User) -> list[CateringSetting]:
        defaults = {
            "allergy_warning_mode": "block_with_override",
            "npo_rule": "do_not_generate_meals",
            "meal_ticket_format": "meal_number,patient_id,ward,bed,diet_type,meal_type,due_time",
            "billing_rule": "bed_package_included_extra_meal_billable",
            "staff_meal_rule": "paid_or_duty_free",
            "kitchen_inventory_store": "Kitchen Store",
        }
        for key, value in defaults.items():
            if not self.db.scalar(select(CateringSetting).where(CateringSetting.setting_key == key)):
                self.db.add(CateringSetting(branch_id=actor.branch_id, setting_key=key, setting_value=value))
        self.db.flush()
        return list(self.db.scalars(select(CateringSetting).where(CateringSetting.is_active.is_(True)).order_by(CateringSetting.setting_key.asc())))

    def upsert_setting(self, payload: CateringSettingCreate, actor: User, context: dict[str, str | None]) -> CateringSetting:
        item = self.db.scalar(select(CateringSetting).where(CateringSetting.setting_key == payload.setting_key))
        if not item:
            item = CateringSetting(branch_id=actor.branch_id, created_by=actor.id)
            self.db.add(item)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.updated_by = actor.id
        self._audit(actor, "catering.settings.update", "catering_setting", item, payload.model_dump(), context)
        return item

    def reports(self, actor: User, report_type: str, filters: dict) -> CateringReportRead:
        meal_date = filters.get("meal_date")
        tasks = self.list_meals(actor, meal_date=meal_date, filters=filters)
        rows: list[dict] = []
        if report_type in {"daily", "delivery", "missed_refused", "special_diet", "allergy_risk", "billable"}:
            for task in tasks:
                if report_type == "missed_refused" and task.delivery_status not in {"missed", "refused"}:
                    continue
                if report_type == "special_diet" and task.safety_status == "clear" and not task.restrictions:
                    continue
                if report_type == "allergy_risk" and not task.allergies:
                    continue
                if report_type == "billable" and not task.billable_amount:
                    continue
                rows.append(self._task_row(task))
        elif report_type == "staff":
            rows = [{"staff_name": item.staff_name, "staff_code": item.staff_code, "meal_date": str(item.meal_date), "meal_type": item.meal_type, "status": item.status, "amount": str(item.amount), "payroll_deductible": item.payroll_deductible} for item in self.list_staff_meals(actor, meal_date)]
        elif report_type == "stock_usage":
            rows = [{"meal_number": usage.meal_task.meal_number if usage.meal_task else None, "item_name": usage.item_name, "quantity_used": str(usage.quantity_used), "unit": usage.unit, "stock_status": usage.stock_status} for usage in self.db.scalars(select(CateringInventoryUsage).options(joinedload(CateringInventoryUsage.meal_task))).unique()]
        return CateringReportRead(report_type=report_type, filters={k: str(v) for k, v in filters.items() if v}, rows=rows, totals={"count": len(rows), "billable_amount": str(sum((Decimal(str(row.get("billable_amount", 0) or 0)) for row in rows), Decimal("0")))})

    def _safety_warnings(self, order: CateringDietOrder) -> list[str]:
        warnings: list[str] = []
        if order.diet_type.is_npo:
            warnings.append("Patient is NPO / nil by mouth")
        allergens = (order.allergies or "").lower()
        plan_allergens = (order.meal_plan.allergens if order.meal_plan else "" or "").lower()
        if allergens and plan_allergens and any(part.strip() and part.strip() in plan_allergens for part in allergens.replace(";", ",").split(",")):
            warnings.append("Meal plan conflicts with documented allergy")
        if order.restrictions and order.meal_plan and any(part.strip() and part.strip().lower() in (order.meal_plan.ingredients or "").lower() for part in order.restrictions.replace(";", ",").split(",")):
            warnings.append("Meal ingredients may conflict with restrictions")
        return warnings

    def _inventory_status(self, meal_plan: CateringMealPlan | None) -> str | None:
        if not meal_plan or not meal_plan.inventory_item:
            return None
        try:
            if Decimal(meal_plan.inventory_item.stock_quantity or 0) < Decimal(meal_plan.inventory_quantity or 0):
                return "shortage"
        except AttributeError:
            return "configured"
        return "reserved"

    def _task_row(self, task: CateringMealTask) -> dict:
        return {
            "meal_number": task.meal_number,
            "ticket_code": task.ticket_code,
            "patient_number": task.patient.patient_number if task.patient else None,
            "patient_name": f"{task.patient.first_name} {task.patient.last_name}".strip() if task.patient else None,
            "ward_name": task.ward_name,
            "bed_number": task.bed_number,
            "diet_type_name": task.diet_type_name,
            "meal_type": task.meal_type,
            "due_at": task.due_at.isoformat(),
            "preparation_status": task.preparation_status,
            "delivery_status": task.delivery_status,
            "patient_response": task.patient_response,
            "billable_amount": str(task.billable_amount),
        }

    def _audit(self, actor: User, action: str, entity_type: str, entity, detail: dict, context: dict[str, str | None]) -> None:
        self.db.flush()
        AuditService(self.db).log(user_id=actor.id, action=action, module="catering", entity_type=entity_type, entity_id=str(entity.id) if entity is not None else None, detail=detail, context=context)
        self.db.commit()
        if entity is not None:
            self.db.refresh(entity)
