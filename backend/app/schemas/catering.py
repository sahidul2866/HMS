from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CateringDashboardRead(BaseModel):
    total_meals_today: int = 0
    pending_meal_orders: int = 0
    under_preparation: int = 0
    ready_for_delivery: int = 0
    delivered: int = 0
    special_diet_patients: int = 0
    npo_patients: int = 0
    allergy_risk_patients: int = 0
    missed_or_delayed: int = 0
    stock_shortages: int = 0
    by_ward: dict[str, int] = {}
    by_diet_type: dict[str, int] = {}
    by_meal_type: dict[str, int] = {}


class CateringDietTypeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=140)
    description: str | None = None
    is_npo: bool = False
    requires_approval: bool = False
    default_restrictions: str | None = None


class CateringDietTypeRead(CateringDietTypeCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class CateringMealPlanCreate(BaseModel):
    diet_type_id: UUID | None = None
    name: str = Field(min_length=2, max_length=160)
    meal_type: str = "lunch"
    description: str | None = None
    ingredients: str | None = None
    allergens: str | None = None
    calories: int | None = None
    protein_grams: Decimal | None = None
    billable_amount: Decimal = Decimal("0")
    inventory_item_id: UUID | None = None
    inventory_quantity: Decimal = Decimal("0")


class CateringMealPlanRead(CateringMealPlanCreate):
    id: UUID
    diet_type_name: str | None = None
    is_active: bool
    model_config = {"from_attributes": True}


class CateringMealScheduleCreate(BaseModel):
    meal_type: str
    display_name: str
    serving_time: time
    cutoff_minutes: int = 60
    sort_order: int = 0


class CateringMealScheduleRead(CateringMealScheduleCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class CateringDietOrderCreate(BaseModel):
    patient_id: UUID
    ipd_admission_id: UUID | None = None
    er_visit_id: UUID | None = None
    diet_type_id: UUID
    meal_plan_id: UUID | None = None
    admission_number: str | None = None
    ward_name: str | None = None
    bed_number: str | None = None
    restrictions: str | None = None
    allergies: str | None = None
    special_instructions: str | None = None
    nutrition_notes: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    requires_approval: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_uuid_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key in ("ipd_admission_id", "er_visit_id", "meal_plan_id"):
                if data.get(key) in {"", "null", "undefined"}:
                    data[key] = None
        return data


class CateringDietOrderUpdate(CateringDietOrderCreate):
    status: str = "active"


class CateringDietOrderRead(CateringDietOrderCreate):
    id: UUID
    branch_id: UUID | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    diet_type_name: str
    meal_plan_name: str | None = None
    status: str
    ordered_by_name: str | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class CateringMealGenerateRequest(BaseModel):
    meal_date: date


class CateringMealStatusUpdate(BaseModel):
    preparation_status: str | None = None
    delivery_status: str | None = None
    received_by: str | None = None
    patient_response: str | None = None
    refusal_reason: str | None = None
    remarks: str | None = None
    override_reason: str | None = None


class CateringMealTaskRead(BaseModel):
    id: UUID
    diet_order_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    patient_number: str | None = None
    meal_plan_id: UUID | None = None
    meal_number: str
    meal_date: date
    meal_type: str
    due_at: datetime
    ward_name: str | None = None
    bed_number: str | None = None
    diet_type_name: str
    restrictions: str | None = None
    allergies: str | None = None
    special_instructions: str | None = None
    preparation_status: str
    delivery_status: str
    safety_status: str
    safety_warnings: list[str] = []
    override_reason: str | None = None
    prepared_by_name: str | None = None
    prepared_at: datetime | None = None
    delivered_by_name: str | None = None
    delivered_at: datetime | None = None
    received_by: str | None = None
    patient_response: str | None = None
    refusal_reason: str | None = None
    remarks: str | None = None
    billable_amount: Decimal
    inventory_status: str | None = None
    ticket_code: str | None = None
    is_active: bool
    created_at: datetime


class CateringStaffMealCreate(BaseModel):
    employee_id: UUID | None = None
    department_id: UUID | None = None
    staff_name: str | None = Field(default=None, max_length=160)
    staff_code: str | None = None
    meal_date: date
    meal_type: str
    eligibility_type: str = "paid"
    amount: Decimal = Decimal("0")
    payroll_deductible: bool = False
    remarks: str | None = None


class CateringStaffMealRead(CateringStaffMealCreate):
    id: UUID
    status: str
    department_name: str | None = None
    token_code: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class CateringSettingCreate(BaseModel):
    setting_key: str = Field(min_length=2, max_length=120)
    setting_value: str
    description: str | None = None
    meta: dict | None = None


class CateringSettingRead(CateringSettingCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class CateringReportRead(BaseModel):
    report_type: str
    filters: dict[str, Any]
    rows: list[dict[str, Any]]
    totals: dict[str, Any]
