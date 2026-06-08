from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class CateringDietType(Base, BaseModelMixin):
    __tablename__ = "catering_diet_types"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_npo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_restrictions: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")


class CateringMealPlan(Base, BaseModelMixin):
    __tablename__ = "catering_meal_plans"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    diet_type_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catering_diet_types.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False, default="lunch")
    description: Mapped[str | None] = mapped_column(Text)
    ingredients: Mapped[str | None] = mapped_column(Text)
    allergens: Mapped[str | None] = mapped_column(Text)
    calories: Mapped[int | None] = mapped_column()
    protein_grams: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    billable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    inventory_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"))
    inventory_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    branch = relationship("Branch")
    diet_type = relationship("CateringDietType")
    inventory_item = relationship("InventoryItem")


class CateringMealSchedule(Base, BaseModelMixin):
    __tablename__ = "catering_meal_schedules"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    serving_time: Mapped[time] = mapped_column(Time(), nullable=False)
    cutoff_minutes: Mapped[int] = mapped_column(nullable=False, default=60)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)

    branch = relationship("Branch")


class CateringDietOrder(Base, BaseModelMixin):
    __tablename__ = "catering_diet_orders"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    ipd_admission_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ipd_admissions.id"))
    er_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("er_visits.id"))
    diet_type_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catering_diet_types.id"), nullable=False)
    meal_plan_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catering_meal_plans.id"))
    admission_number: Mapped[str | None] = mapped_column(String(80))
    ward_name: Mapped[str | None] = mapped_column(String(120), index=True)
    bed_number: Mapped[str | None] = mapped_column(String(80), index=True)
    restrictions: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[str | None] = mapped_column(Text)
    special_instructions: Mapped[str | None] = mapped_column(Text)
    nutrition_notes: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    ordered_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    branch = relationship("Branch")
    patient = relationship("Patient")
    ipd_admission = relationship("IPDAdmission")
    er_visit = relationship("ERVisit")
    diet_type = relationship("CateringDietType")
    meal_plan = relationship("CateringMealPlan")
    ordered_by = relationship("User", foreign_keys=[ordered_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])


class CateringMealTask(Base, BaseModelMixin):
    __tablename__ = "catering_meal_tasks"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    diet_order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catering_diet_orders.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    meal_plan_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catering_meal_plans.id"))
    meal_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    meal_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ward_name: Mapped[str | None] = mapped_column(String(120), index=True)
    bed_number: Mapped[str | None] = mapped_column(String(80), index=True)
    diet_type_name: Mapped[str] = mapped_column(String(140), nullable=False)
    restrictions: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[str | None] = mapped_column(Text)
    special_instructions: Mapped[str | None] = mapped_column(Text)
    preparation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="scheduled")
    delivery_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    safety_status: Mapped[str] = mapped_column(String(40), nullable=False, default="clear")
    safety_warnings: Mapped[list | None] = mapped_column(JSON)
    override_reason: Mapped[str | None] = mapped_column(Text)
    prepared_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[str | None] = mapped_column(String(150))
    patient_response: Mapped[str | None] = mapped_column(String(40))
    refusal_reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    billable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    inventory_status: Mapped[str | None] = mapped_column(String(40))
    ticket_code: Mapped[str | None] = mapped_column(String(120), unique=True)

    branch = relationship("Branch")
    diet_order = relationship("CateringDietOrder")
    patient = relationship("Patient")
    meal_plan = relationship("CateringMealPlan")
    prepared_by = relationship("User", foreign_keys=[prepared_by_user_id])
    delivered_by = relationship("User", foreign_keys=[delivered_by_user_id])
    billing_invoice = relationship("BillingInvoice")


class CateringStaffMealOrder(Base, BaseModelMixin):
    __tablename__ = "catering_staff_meal_orders"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    staff_name: Mapped[str] = mapped_column(String(160), nullable=False)
    staff_code: Mapped[str | None] = mapped_column(String(80))
    meal_date: Mapped[date] = mapped_column(Date(), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    eligibility_type: Mapped[str] = mapped_column(String(50), nullable=False, default="paid")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ordered")
    token_code: Mapped[str | None] = mapped_column(String(120), unique=True)
    payroll_deductible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    employee = relationship("HREmployee")
    department = relationship("Department")


class CateringInventoryUsage(Base, BaseModelMixin):
    __tablename__ = "catering_inventory_usage"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    meal_task_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catering_meal_tasks.id"))
    inventory_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_items.id"))
    item_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(40))
    stock_status: Mapped[str] = mapped_column(String(40), nullable=False, default="recorded")
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    meal_task = relationship("CateringMealTask")
    inventory_item = relationship("InventoryItem")


class CateringSetting(Base, BaseModelMixin):
    __tablename__ = "catering_settings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON)

    branch = relationship("Branch")
